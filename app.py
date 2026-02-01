import re
import ast
import json
from io import StringIO

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Picking List Generator", layout="wide")

st.title("Picking List Generator (Seller SKU → Name + S/M/L + Subtotal)")

st.markdown(
    """
功能：
- 输入 Seller SKU 列表（每行一个，如 `NPX017-S`）
- 输入/粘贴 SKU→Name 对照表（Python dict 或 JSON 都可）
- 输出按 **Name 字母顺序**排列的拣货汇总表：Name | Base SKU | S | M | L | Subtotal
- 缺失尺码自动补 0
- 无尺码 SKU（如 NF001）不计入 S/M/L，只计入 Subtotal
"""
)

# ----------------------------
# Helpers
# ----------------------------
SIZE_SET = {"S", "M", "L"}

def parse_seller_sku_line(line: str):
    """
    Parse a seller sku line into (base_sku, size or None).
    Examples:
      NPX017-S -> ("NPX017", "S")
      NF001    -> ("NF001", None)
      NOF011-M -> ("NOF011", "M")
    """
    s = line.strip()
    if not s:
        return None

    # Try match "...-S|M|L" at end
    m = re.match(r"^([A-Z0-9]+)-([SML])$", s)
    if m:
        return m.group(1), m.group(2)

    # If line contains other suffixes (like -XL etc), treat as "no size"
    # but keep base as the full string before first whitespace
    m2 = re.match(r"^([A-Z0-9]+)$", s)
    if m2:
        return s, None

    # Fallback: extract first token that looks like SKU
    m3 = re.search(r"([A-Z]{1,3}[A-Z0-9]{2,})", s)
    if m3:
        token = m3.group(1)
        # check if token itself ends with -S etc (rare in fallback)
        m4 = re.match(r"^([A-Z0-9]+)-([SML])$", token)
        if m4:
            return m4.group(1), m4.group(2)
        return token, None

    return None


def load_mapping(mapping_text: str) -> dict:
    """
    Accept mapping in:
    - Python dict literal: {"NPX017":"Rouge Letter", ...}
    - JSON object
    - Partial dict lines separated by commas (we'll wrap in { } if needed)
    """
    txt = mapping_text.strip()
    if not txt:
        return {}

    # If user pasted a "dict body" without braces, add braces
    if not (txt.startswith("{") and txt.endswith("}")):
        # try wrapping
        txt_wrapped = "{" + txt + "}"
    else:
        txt_wrapped = txt

    # Try JSON first
    try:
        obj = json.loads(txt_wrapped)
        if isinstance(obj, dict):
            return {str(k).strip(): str(v).strip() for k, v in obj.items()}
    except Exception:
        pass

    # Try Python literal
    try:
        obj = ast.literal_eval(txt_wrapped)
        if isinstance(obj, dict):
            return {str(k).strip(): str(v).strip() for k, v in obj.items()}
    except Exception as e:
        raise ValueError(
            "对照表解析失败：请粘贴 Python dict 或 JSON 格式，例如：\n"
            '{"NPX017":"Rouge Letter","NF001":"Free Giveaway"}\n\n'
            f"错误信息：{e}"
        )

    raise ValueError("对照表解析失败：未识别为 dict/JSON。")


def build_picking_table(seller_skus: list[str], mapping: dict):
    """
    Return:
      df_out: Name/Base/S/M/L/Subtotal aggregated
      audit: dict with totals and missing mapping info
    """
    rows = []
    for line in seller_skus:
        parsed = parse_seller_sku_line(line)
        if not parsed:
            continue
        base, size = parsed
        rows.append({"raw": line.strip(), "base_sku": base, "size": size})

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["Name", "Base SKU", "S", "M", "L", "Subtotal"]), {
            "raw_lines": 0,
            "valid_lines": 0,
            "sml_total": 0,
            "nosize_total": 0,
            "grand_total": 0,
            "missing_name_bases": []
        }

    # Count original valid lines
    valid_lines = len(df)

    # Sized vs no-size split
    df_sized = df[df["size"].isin(list(SIZE_SET))].copy()
    df_nosize = df[df["size"].isna()].copy()

    # Pivot sized
    if not df_sized.empty:
        pivot = (
            df_sized.groupby(["base_sku", "size"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
    else:
        pivot = pd.DataFrame({"base_sku": []})

    # Ensure S/M/L columns exist
    for col in ["S", "M", "L"]:
        if col not in pivot.columns:
            pivot[col] = 0

    # No-size counts per base
    nosize_counts = (
        df_nosize.groupby("base_sku")
        .size()
        .rename("NOSIZE")
        .reset_index()
        if not df_nosize.empty
        else pd.DataFrame({"base_sku": [], "NOSIZE": []})
    )

    # Merge sized pivot + nosize
    merged = pivot.merge(nosize_counts, on="base_sku", how="outer").fillna(0)
    merged["S"] = merged["S"].astype(int)
    merged["M"] = merged["M"].astype(int)
    merged["L"] = merged["L"].astype(int)
    merged["NOSIZE"] = merged["NOSIZE"].astype(int)

    # Subtotal: S+M+L+NOSIZE
    merged["Subtotal"] = merged["S"] + merged["M"] + merged["L"] + merged["NOSIZE"]

    # Attach Name
    merged["Name"] = merged["base_sku"].map(mapping).fillna("UNKNOWN")

    # Output formatting
    df_out = merged.rename(columns={"base_sku": "Base SKU"})[
        ["Name", "Base SKU", "S", "M", "L", "Subtotal"]
    ].copy()

    # Sort by Name then Base SKU
    # Keep UNKNOWN at the bottom
    df_out["__unknown_flag"] = (df_out["Name"] == "UNKNOWN").astype(int)
    df_out = df_out.sort_values(by=["__unknown_flag", "Name", "Base SKU"], ascending=[True, True, True])
    df_out = df_out.drop(columns=["__unknown_flag"]).reset_index(drop=True)

    # Audits
    sml_total = int(df_out["S"].sum() + df_out["M"].sum() + df_out["L"].sum())
    grand_total = int(df_out["Subtotal"].sum())
    nosize_total = int(grand_total - sml_total)

    missing_name_bases = sorted(df_out.loc[df_out["Name"] == "UNKNOWN", "Base SKU"].unique().tolist())

    audit = {
        "raw_lines": len(seller_skus),
        "valid_lines": valid_lines,
        "sml_total": sml_total,
        "nosize_total": nosize_total,
        "grand_total": grand_total,
        "missing_name_bases": missing_name_bases,
    }
    return df_out, audit


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


# ----------------------------
# UI
# ----------------------------
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1) Seller SKU 列表（每行一个）")
    seller_input = st.text_area(
        "粘贴你的 Seller SKU（支持含表头、空行，会自动忽略）",
        height=350,
        placeholder="NPX017-S\nNHF001-M\nNF001\n..."
    )

with col2:
    st.subheader("2) SKU ↔ Name 对照表（dict / JSON）")
    mapping_input = st.text_area(
        "粘贴完整对照表（Python dict 或 JSON）",
        height=350,
        placeholder='{"NPX017":"Rouge Letter","NF001":"Free Giveaway"}'
    )

st.divider()

# Run
if st.button("生成拣货表", type="primary"):
    # Parse seller SKUs
    raw_lines = [ln.strip() for ln in seller_input.splitlines()]
    # Drop common header lines
    header_blacklist = {
        "seller sku", "seller sku input by the seller in the product system.", "seller sku input by the seller in the product system"
    }
    seller_lines = []
    for ln in raw_lines:
        if not ln:
            continue
        if ln.strip().lower() in header_blacklist:
            continue
        seller_lines.append(ln)

    # Load mapping
    try:
        mapping = load_mapping(mapping_input)
    except Exception as e:
        st.error(str(e))
        st.stop()

    df_out, audit = build_picking_table(seller_lines, mapping)

    # Show audits
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("原始输入行数（非空）", audit["raw_lines"])
    a2.metric("有效SKU行数", audit["valid_lines"])
    a3.metric("S+M+L 合计", audit["sml_total"])
    a4.metric("总计（含无尺码）", audit["grand_total"])

    st.caption(f"无尺码合计（如 NF001）：{audit['nosize_total']}")

    if audit["grand_total"] != audit["valid_lines"]:
        st.warning(
            f"⚠️ 校验不一致：有效SKU行数={audit['valid_lines']}，汇总总计={audit['grand_total']}。\n"
            "这通常意味着输入里存在未被解析的格式（例如带空格/特殊字符/不规范SKU）。"
        )
    else:
        st.success("✅ 校验通过：汇总总计与有效SKU行数一致。")

    # Missing names
    if audit["missing_name_bases"]:
        st.warning("以下 Base SKU 在对照表中未找到 Name（已标记为 UNKNOWN）：")
        st.code(", ".join(audit["missing_name_bases"]))

    st.subheader("3) 拣货汇总表")
    st.dataframe(df_out, use_container_width=True, hide_index=True)

    # Download CSV
    st.download_button(
        label="下载 CSV",
        data=to_csv_bytes(df_out),
        file_name="picking_list.csv",
        mime="text/csv"
    )

    # Optional: show raw pivot debug
    with st.expander("（可选）显示汇总逻辑说明"):
        st.write(
            "Subtotal = S + M + L + (无尺码数量)。\n"
            "无尺码 SKU（例如 NF001）不会进入 S/M/L，只计入 Subtotal。"
        )
