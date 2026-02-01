import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Temp Picking Console", layout="wide")
st.title("Temp Picking Console")
st.caption("输入 Seller SKU 列表（粘贴 / 上传 CSV / 上传 Excel）→ 输出 Name × S/M/L × 小计，并导出 CSV")

# =====================================================
# 内置完整 SKU → Name 映射表（你给的最终版）
# =====================================================
SKU_NAME_MAP = {
    "NDF001":"Tropic Paradise","NPX014":"Afterglow","NDX001":"Pinky Promise","NHF001":"Gothic Moon","NHX001":"Emerald Garden",
    "NLF001":"Divine Emblem","NLF002":"Athena's Glow","NLJ001":"Golden Pearl","NLJ002":"BAROQUE BLISS","NLJ003":"Rainbow Reef",
    "NLX001":"Mermaid's Whisper","NLX003":"Tropical Tide","NLX005":"Pure Grace","NOF001":"Royal Amber","NOF002":"Tiger Lily",
    "NOF003":"Peach Pop","NOF004":"Sunset Punch","NOF005":"Glacier Petal","NOJ001":"Island Bloom","NOJ002":"Floral Lemonade",
    "NOJ003":"Aurora Tide","NOX001":"Lava Latte","NPD001":"Leopard's Kiss","NPF001":"Angel's Grace","NPF002":"Sacred Radiance",
    "NPF003":"Golden Ivy","NPF005":"Auric Taurus","NPF006":"Cocoa Blossom","NPF007":"Bluebell Glow","NPF008":"Lavender Angel",
    "NPF009":"Vintage Bloom","NPF010":"Pastel Meadow","NPF011":"Cherry Cheetah","NPF012":"Rosey Tigress","NPJ001":"SCARLET QUEEN",
    "NPJ003":"Stellar Capricorn","NPJ004":"Midnight Violet","NPJ005":"Vintage Cherry","NPJ006":"Savanna Bloom","NPJ007":"Angel's Blush",
    "NPJ008":"Gothic Sky","NPJ009":"Violet Seashell","NPX001":"Royal Elegance","NPX002":"Angel's Ruby","NPX005":"Indigo Breeze",
    "NPX006":"Autumn Petal","NPX007":"Lavender Bliss","NPX008":"Dreamy Ballerina","NPX009":"Rose Eden","NPX010":"Blooming Meadow",
    "NPX011":"Safari Petal","NPX012":"Milky Ribbon","NPX013":"Champagne Wishes","NLX004":"Holiday Bunny","NPJ010":"Glossy Doll",
    "NPF013":"Opal Glaze","NOX002":"Cherry Kiss","NOJ004":"Peachy Coast","NYJ001":"Rosy Ribbon","NOF008":"Starlit Jungle",
    "NOF006":"Coral Sea","NOF009":"Rosé Angel","NPF014":"Arabian Nights","NOX003":"Caramel Nova","NPF016":"Golden Muse",
    "NPF017":"Ruby Bloom","NOF007":"Citrus Blush","NOJ005":"Ocean Whisper","NPF015":"Rosé Petal","NOF010":"Spring Moss",
    "NM001":"Mystery Set","NOF011":"Velvet Flame","NPJ011":"Bat Boo","NOX004":"Azure Muse","NPX016":"Silky Pearl",
    "NPX015":"Spooky Clown","NOX005":"Honey Daisy","NPJ012":"Gothic Mirage","NOX006":"Imperial Bloom","NPX017":"Rouge Letter",
    "NOF013":"Sakura Blush","NPF018":"Wild Berry","NOF012":"Rose Nocturne","NIX001":"Golden Maple","NOX007":"Stellar Whisper",
    "NOF014":"Desert Rose","NPF019":"Lunar Whisper","NOF015":"Mocha Grace","NOX009":"Moonlit Petal","NOX008":"Espresso Petals",
    "NPX018":"Ruby Ribbon","NPF020":"Amber Mist","NOJ006":"Toffee Muse","NOJ007":"Cherry Glaze","NOX011":"Opal Mirage",
    "NOF016":"Cinnamon Bloom","NOX010":"Twilight Muse","NPX020":"Peachy Glaze","NPX019":"Blossom Tart","NPJ013":"Velvet Cherry",
    "NOX012":"Harvest Glaze","NOJ008":"Crystal Whisper","NOF017":"Twinkle Bow","NPX021":"Twinkle Pine","NOF018":"Glacier Bloom",
    "NOJ010":"Rosé Noir","NPX022":"Merry Charm","NPF022":"Holiday Sparkl","NOF020":"Garnet Muse","NOF019":"Twinkle Christmas",
    "NOJ011":"Snowy Comet","NOX013":"Christmas Village","NOJ009":"Reindeer Glow","NIX002":"Golden Orchid",
    "NPJ014":"Snow Pixie","NPJ018":"Frost Ruby","NPJ017":"Starlit Rift","NPF021":"Candy Cane","NPJ016":"Fairy Nectar",
    "NPJ015":"Icy Viper","NOX014":"Taro Petal","NVT001":"Tool Kits","NF001":"Free Giveaway",
    "NIF001":"Lilac Veil","NIF002":"Gingerbread","NOX015":"Glitter Doll","NOJ012":"Winery Flame",
    "NOF021":"Velvet Ribbon","NPX024":"Rose Wine","NPX023":"Rosy Promise","NMF001":"Cherry Crush",
    "NBX001":"Ballet Petal","NMF003":"Royal Treasure","NMF002":"Safari Princess",
    "NOJ013":"Midnight Denim","NOJ014":"Imperial Frost","NPJ019":"Gothic Mist","NOJ015":"Sapphire Bloom",
    "NPX025":"Cocoa Teddy","NVF001":"Golden Bloom","NBJ002":"Cherry Drop","NOF022":"Aqua Reverie",
    "NPF023":"Arctic Starlight","NDJ001":"Snow Knit","NOX016":"Cherry Ribbon","NOX017":"Ruby Bow",
    "NMF004":"Lavender Bloom","NDX002":"Cloudy Knit","NMJ003":"Gothic Rose","NOF025":"Cherry Romance",
    "NMJ001":"Milky Cloud","NMX001":"Petal Muse","NOF024":"Floral Muse"
}

# =====================================================
# Helpers
# =====================================================
SIZE_SET = {"S", "M", "L"}

def normalize_colname(s: str) -> str:
    """Lowercase, remove spaces/underscores for robust matching."""
    return re.sub(r"[\s_]+", "", str(s).strip().lower())

def parse_sku(line: str):
    """Return (base_sku, size_or_None) or None."""
    if line is None:
        return None
    s = str(line).strip()
    if not s:
        return None

    # exact form: BASE-S|M|L
    m = re.match(r"^([A-Z0-9]+)-([SML])$", s)
    if m:
        return m.group(1), m.group(2)

    # no-size: BASE only
    if re.match(r"^[A-Z0-9]+$", s):
        return s, None

    # if there are extra spaces or text, try to extract SKU token
    token = re.search(r"([A-Z0-9]+(?:-[SML])?)", s)
    if token:
        t = token.group(1)
        m2 = re.match(r"^([A-Z0-9]+)-([SML])$", t)
        if m2:
            return m2.group(1), m2.group(2)
        if re.match(r"^[A-Z0-9]+$", t):
            return t, None

    return None

def build_picking_table(sku_list: list[str]) -> tuple[pd.DataFrame, dict]:
    """Aggregate into Name|Base SKU|S|M|L|Subtotal, with audits."""
    parsed_rows = []
    for x in sku_list:
        res = parse_sku(x)
        if not res:
            continue
        base, size = res
        parsed_rows.append({"base": base, "size": size})

    df = pd.DataFrame(parsed_rows)
    if df.empty:
        return pd.DataFrame(columns=["Name","Base SKU","S","M","L","Subtotal"]), {
            "input_lines": len(sku_list),
            "parsed_lines": 0,
            "sml_total": 0,
            "nosize_total": 0,
            "grand_total": 0,
            "unknown_bases": []
        }

    parsed_lines = len(df)

    sized = df[df["size"].isin(list(SIZE_SET))].copy()
    nosize = df[df["size"].isna()].copy()

    if not sized.empty:
        pivot = sized.groupby(["base","size"]).size().unstack(fill_value=0).reset_index()
    else:
        pivot = pd.DataFrame({"base": []})

    for c in ["S","M","L"]:
        if c not in pivot.columns:
            pivot[c] = 0

    nosize_cnt = nosize.groupby("base").size().reset_index(name="NOSIZE") if not nosize.empty else pd.DataFrame({"base": [], "NOSIZE": []})

    out = pivot.merge(nosize_cnt, on="base", how="outer").fillna(0)
    out[["S","M","L","NOSIZE"]] = out[["S","M","L","NOSIZE"]].astype(int)

    out["Subtotal"] = out["S"] + out["M"] + out["L"] + out["NOSIZE"]
    out["Name"] = out["base"].map(SKU_NAME_MAP).fillna("UNKNOWN")

    df_out = out.rename(columns={"base":"Base SKU"})[["Name","Base SKU","S","M","L","Subtotal"]].copy()

    # sort by name, keep UNKNOWN last
    df_out["_unk"] = (df_out["Name"] == "UNKNOWN").astype(int)
    df_out = df_out.sort_values(["_unk","Name","Base SKU"]).drop(columns="_unk").reset_index(drop=True)

    sml_total = int(df_out["S"].sum() + df_out["M"].sum() + df_out["L"].sum())
    grand_total = int(df_out["Subtotal"].sum())
    nosize_total = int(grand_total - sml_total)

    unknown_bases = sorted(df_out.loc[df_out["Name"]=="UNKNOWN", "Base SKU"].unique().tolist())

    audit = {
        "input_lines": len(sku_list),
        "parsed_lines": parsed_lines,
        "sml_total": sml_total,
        "nosize_total": nosize_total,
        "grand_total": grand_total,
        "unknown_bases": unknown_bases
    }
    return df_out, audit

def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")

# =====================================================
# UI
# =====================================================
st.subheader("输入方式")
mode = st.radio("选择一种输入方式", ["上传文件（CSV / Excel）", "粘贴文本（每行一个 SKU）"], horizontal=True)

sku_list = []

if mode == "上传文件（CSV / Excel）":
    uploaded = st.file_uploader("上传 CSV 或 Excel（.xlsx）", type=["csv", "xlsx"])
    if uploaded is not None:
        # Read file
        try:
            if uploaded.name.lower().endswith(".csv"):
                df_in = pd.read_csv(uploaded)
            else:
                df_in = pd.read_excel(uploaded)
        except Exception as e:
            st.error(f"文件读取失败：{e}")
            st.stop()

        st.write("文件预览：")
        st.dataframe(df_in.head(20), use_container_width=True)

        # Auto-detect SKU column
        candidates = []
        norm_to_raw = {normalize_colname(c): c for c in df_in.columns}

        preferred_norms = [
            normalize_colname("Seller SKU"),
            normalize_colname("Seller sku"),
            normalize_colname("seller_sku"),
            normalize_colname("SellerSKU"),
            normalize_colname("SKU"),
            normalize_colname("Platform SKU"),
        ]

        for p in preferred_norms:
            if p in norm_to_raw:
                candidates.append(norm_to_raw[p])

        # Fallback: any col contains 'sku'
        if not candidates:
            for c in df_in.columns:
                if "sku" in normalize_colname(c):
                    candidates.append(c)

        col_pick = st.selectbox(
            "选择 SKU 列（自动识别结果可直接用，也可手动改）",
            options=df_in.columns.tolist(),
            index=(df_in.columns.get_loc(candidates[0]) if candidates else 0)
        )

        # Build sku list from selected column
        sku_series = df_in[col_pick].dropna().astype(str).tolist()
        sku_list = [s.strip() for s in sku_series if s.strip()]

        st.info(f"已读取 {len(sku_list)} 行 SKU（来自列：{col_pick}）")

else:
    sku_text = st.text_area(
        "粘贴 Seller SKU（每行一个）",
        height=260,
        placeholder="NPX017-S\nNHF001-M\nNF001\n..."
    )
    lines = [ln.strip() for ln in sku_text.splitlines() if ln.strip()]
    # ignore simple header variants
    header_blacklist = {"seller sku", "seller sku input by the seller in the product system"}
    sku_list = [ln for ln in lines if ln.strip().lower() not in header_blacklist]
    st.info(f"已读取 {len(sku_list)} 行 SKU（粘贴输入）")

st.divider()

if st.button("生成拣货表", type="primary", disabled=(len(sku_list) == 0)):
    df_out, audit = build_picking_table(sku_list)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("输入行数", audit["input_lines"])
    c2.metric("成功解析行数", audit["parsed_lines"])
    c3.metric("S+M+L 合计", audit["sml_total"])
    c4.metric("总计（含无尺码）", audit["grand_total"])

    if audit["grand_total"] != audit["parsed_lines"]:
        st.error(
            "⚠️ 校验失败：汇总总计 != 解析行数。\n"
            "通常是输入里存在格式异常（例如多余字符、逗号、SKU 被拆列）。"
        )
    else:
        st.success("✅ 校验通过：汇总总计与解析行数一致")

    if audit["unknown_bases"]:
        st.warning("以下 Base SKU 在映射表中未找到（标记为 UNKNOWN）：")
        st.code(", ".join(audit["unknown_bases"]))

    st.subheader("拣货汇总表（Name 第一列，缺尺码=0，按 Name 排序）")
    st.dataframe(df_out, use_container_width=True)

    st.download_button(
        "下载 CSV",
        data=csv_bytes(df_out),
        file_name="temp_picking_list.csv",
        mime="text/csv"
    )
