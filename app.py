import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Temp Picking Console", layout="wide")
st.title("Temp Picking Console")
st.caption("两个独立功能：A) 拣货汇总表（按 Name 排序）  B) 售出数字列（固定 SKU 顺序、无表头）")

# =====================================================
# SKU -> Name 映射（你给的最终版）
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
    "NMJ001":"Milky Cloud","NMX001":"Petal Muse","NOF024":"Floral Muse"，“NB001”：“Nail Book”
}

# =====================================================
# 固定 SKU 顺序（只用于“售出数字列”）
# =====================================================
FIXED_SKU_ORDER_TEXT = """NPF001-S
NPF001-M
NPF001-L
NPF005-S
NPF005-M
NPF005-L
NPF002-S
NPF002-M
NPF002-L
NPJ005-S
NPJ005-M
NPJ005-L
NPJ004-S
NPJ004-M
NPJ004-L
NLJ002-S
NLJ002-M
NLJ002-L
NPX005-S
NPX005-M
NPX005-L
NPX002-S
NPX002-M
NPX002-L
NPX001-S
NPX001-M
NPX001-L
NPX007-S
NPX007-M
NPX007-L
NPF007-S
NPF007-M
NPF007-L
NPF009-S
NPF009-M
NPF009-L
NPJ007-S
NPJ007-M
NPJ007-L
NPX009-S
NPX009-M
NPX009-L
NHF001-S
NHF001-M
NHF001-L
NPF012-S
NPF012-M
NPF012-L
NOF001-S
NOF001-M
NOF001-L
NDF001-S
NDF001-M
NDF001-L
NDX001-S
NDX001-M
NDX001-L
NPX013-S
NPX013-M
NPX013-L
NPX014-S
NPX014-M
NPX014-L
NOF008-S
NOF008-M
NOF008-L
NOF009-S
NOF009-M
NOF009-L
NPF014-S
NPF014-M
NPF014-L
NPF016-S
NPF016-M
NPF016-L
NPF017-S
NPF017-M
NPF017-L
NPF015-S
NPF015-M
NPF015-L
NOF011-S
NOF011-M
NOF011-L
NOF010-S
NOF010-M
NOF010-L
NOX004-S
NOX004-M
NOX004-L
NPX016-S
NPX016-M
NPX016-L
NOF013-S
NOF013-M
NOF013-L
NPX017-S
NPX017-M
NPX017-L
NOF012-S
NOF012-M
NOF012-L
NPJ012-S
NPJ012-M
NPJ012-L
NPF018-S
NPF018-M
NPF018-L
NOX006-S
NOX006-M
NOX006-L
NIX001-S
NIX001-M
NIX001-L
NOX007-S
NOX007-M
NOX007-L
NOF014-S
NOF014-M
NOF014-L
NPF019-S
NPF019-M
NPF019-L
NOF015-S
NOF015-M
NOF015-L
NOX009-S
NOX009-M
NOX009-L
NOX008-S
NOX008-M
NOX008-L
NPX018-S
NPX018-M
NPX018-L
NPF020-S
NPF020-M
NPF020-L
NOJ006-S
NOJ006-M
NOJ006-L
NOJ007-S
NOJ007-M
NOJ007-L
NOX011-S
NOX011-M
NOX011-L
NOF016-S
NOF016-M
NOF016-L
NPX020-S
NPX020-M
NPX020-L
NPX019-S
NPX019-M
NPX019-L
NPJ013-S
NPJ013-M
NPJ013-L
NOX012-S
NOX012-M
NOX012-L
NOJ008-S
NOJ008-M
NOJ008-L
NOF018-S
NOF018-M
NOF018-L
NOJ010-S
NOJ010-M
NOJ010-L
NIX002-S
NIX002-M
NIX002-L
NPJ014-S
NPJ014-M
NPJ014-L
NPJ017-S
NPJ017-M
NPJ017-L
NPJ016-S
NPJ016-M
NPJ016-L
NPJ015-S
NPJ015-M
NPJ015-L
NOX014-S
NOX014-M
NOX014-L
NIF001-S
NIF001-M
NIF001-L
NOX015-S
NOX015-M
NOX015-L
NPX024-S
NPX024-M
NPX024-L
NPX023-S
NPX023-M
NPX023-L
NMF001-S
NMF001-M
NMF001-L
NOF021-S
NOF021-M
NOF021-L
NOJ012-S
NOJ012-M
NOJ012-L
NMF002-S
NMF002-M
NMF002-L
NMF003-S
NMF003-M
NMF003-L
NBX001-S
NBX001-M
NBX001-L
NOJ014-S
NOJ014-M
NOJ014-L
NOJ013-S
NOJ013-M
NOJ013-L
NVF001-S
NVF001-M
NVF001-L
NPX025-S
NPX025-M
NPX025-L
NPJ019-S
NPJ019-M
NPJ019-L
NOJ015-S
NOJ015-M
NOJ015-L
NOF022-S
NOF022-M
NOF022-L
NOF023-S
NOF023-M
NOF023-L
NDJ001-S
NDJ001-M
NDJ001-L
NOX016-S
NOX016-M
NOX016-L
NOX017-S
NOX017-M
NOX017-L
NMF004-S
NMF004-M
NMF004-L
NDX002-S
NDX002-M
NDX002-L
NMJ003-S
NMJ003-M
NMJ003-L
NOF025-S
NOF025-M
NOF025-L
NMJ001-S
NMJ001-M
NMJ001-L
NMX001-S
NMX001-M
NMX001-L
NOF024-S
NOF024-M
NOF024-L"""

FIXED_SKU_ORDER = [x.strip() for x in FIXED_SKU_ORDER_TEXT.splitlines() if x.strip()]
FIXED_SKU_SET = set(FIXED_SKU_ORDER)
SIZE_SET = {"S", "M", "L"}


def normalize_colname(s: str) -> str:
    return re.sub(r"[\s_]+", "", str(s).strip().lower())


def parse_sku_strict(x: object):
    """
    严格只接受：
      - BASE-S/M/L
      - BASE（无尺码）
    """
    if x is None:
        return ("", "", None, False)
    s = str(x).strip()
    if not s:
        return ("", "", None, False)

    m = re.match(r"^([A-Z0-9]+)-([SML])$", s)
    if m:
        return (s, m.group(1), m.group(2), True)

    if re.match(r"^[A-Z0-9]+$", s):
        return (s, s, None, True)

    return (s, "", None, False)


def csv_bytes(df: pd.DataFrame, header=True) -> bytes:
    return df.to_csv(index=False, header=header).encode("utf-8-sig")


def build_picking_summary(df_parsed: pd.DataFrame):
    """
    拣货汇总表：Name | Base SKU | S | M | L | Subtotal
    按 Name 字母顺序；UNKNOWN 最后
    """
    valid_df = df_parsed[df_parsed["valid"]].copy()
    if valid_df.empty:
        empty = pd.DataFrame(columns=["Name", "Base SKU", "S", "M", "L", "Subtotal"])
        return empty, {"parsed_lines": 0, "grand_total": 0, "unknown_bases": []}

    sized = valid_df[valid_df["size"].isin(list(SIZE_SET))]
    nosize = valid_df[valid_df["size"].isna()]

    if not sized.empty:
        pivot = sized.groupby(["base", "size"]).size().unstack(fill_value=0).reset_index()
    else:
        pivot = pd.DataFrame({"base": []})

    for c in ["S", "M", "L"]:
        if c not in pivot.columns:
            pivot[c] = 0

    nosize_cnt = (
        nosize.groupby("base").size().reset_index(name="NOSIZE")
        if not nosize.empty else pd.DataFrame({"base": [], "NOSIZE": []})
    )

    out = pivot.merge(nosize_cnt, on="base", how="outer").fillna(0)
    out[["S", "M", "L", "NOSIZE"]] = out[["S", "M", "L", "NOSIZE"]].astype(int)

    out["Subtotal"] = out["S"] + out["M"] + out["L"] + out["NOSIZE"]
    out["Name"] = out["base"].map(SKU_NAME_MAP).fillna("UNKNOWN")

    df_out = out.rename(columns={"base": "Base SKU"})[["Name", "Base SKU", "S", "M", "L", "Subtotal"]].copy()
    df_out["_unk"] = (df_out["Name"] == "UNKNOWN").astype(int)
    df_out = df_out.sort_values(["_unk", "Name", "Base SKU"]).drop(columns="_unk").reset_index(drop=True)

    unknown_bases = sorted(df_out.loc[df_out["Name"] == "UNKNOWN", "Base SKU"].unique().tolist())
    audit = {"parsed_lines": int(len(valid_df)), "grand_total": int(df_out["Subtotal"].sum()), "unknown_bases": unknown_bases}
    return df_out, audit


def build_sold_qty_fixed_order(df_parsed: pd.DataFrame):
    """
    售出数字列：严格按 FIXED_SKU_ORDER 输出（无表头）
      - FIXED 里没出现 => 0
      - 拣货单里出现了带尺码 SKU 但不在 FIXED => 报错
      - 行数 = len(FIXED_SKU_ORDER)
    """
    valid_df = df_parsed[df_parsed["valid"]].copy()
    sized_skus = valid_df.loc[valid_df["size"].isin(list(SIZE_SET)), "raw_sku"].tolist()

    unknown_in_input = sorted(set([s for s in sized_skus if s not in FIXED_SKU_SET]))
    if unknown_in_input:
        raise ValueError(
            "拣货单中出现了不在固定SKU清单里的 SKU（带尺码）：\n" + "\n".join(unknown_in_input)
        )

    counts = pd.Series(sized_skus).value_counts().to_dict()
    sold = [int(counts.get(sku, 0)) for sku in FIXED_SKU_ORDER]

    # 强制行数一致
    if len(sold) != len(FIXED_SKU_ORDER):
        raise ValueError("内部错误：售出列行数不一致（请检查固定 SKU 列表）")

    return pd.DataFrame(sold)


# =====================================================
# 输入区（一次输入，两边功能共用）
# =====================================================
st.subheader("输入")
mode = st.radio("选择一种输入方式", ["上传文件（CSV / Excel）", "粘贴文本（每行一个 SKU）"], horizontal=True)

sku_series = None

if mode == "上传文件（CSV / Excel）":
    uploaded = st.file_uploader("上传 CSV 或 Excel（.xlsx）", type=["csv", "xlsx"])
    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df_in = pd.read_csv(uploaded)
            else:
                df_in = pd.read_excel(uploaded)
        except ImportError as e:
            if "openpyxl" in str(e):
                st.error("缺少 openpyxl：pip install openpyxl，然后重启 Streamlit。")
                st.stop()
            raise
        except Exception as e:
            st.error(f"文件读取失败：{e}")
            st.stop()

        st.write("文件预览：")
        st.dataframe(df_in.head(20), use_container_width=True)

        # 自动识别 SKU 列 + 可手选
        norm_to_raw = {normalize_colname(c): c for c in df_in.columns}
        preferred_norms = [normalize_colname(x) for x in ["Seller SKU", "SellerSKU", "seller_sku", "SKU", "Platform SKU"]]

        guess = None
        for p in preferred_norms:
            if p in norm_to_raw:
                guess = norm_to_raw[p]
                break
        if guess is None:
            for c in df_in.columns:
                if "sku" in normalize_colname(c):
                    guess = c
                    break

        col_pick = st.selectbox(
            "选择 SKU 列",
            options=df_in.columns.tolist(),
            index=(df_in.columns.get_loc(guess) if guess in df_in.columns else 0)
        )
        sku_series = df_in[col_pick]

else:
    sku_text = st.text_area("粘贴 Seller SKU（每行一个）", height=240, placeholder="NPX017-S\nNHF001-M\nNF001\n...")
    lines = [ln.strip() for ln in sku_text.splitlines() if ln.strip()]
    header_blacklist = {"seller sku", "seller sku input by the seller in the product system"}
    lines = [ln for ln in lines if ln.lower() not in header_blacklist]
    sku_series = pd.Series(lines)

# 统一解析（一次解析，两边按钮复用）
df_parsed = None
if sku_series is not None and len(sku_series) > 0:
    parsed = []
    for x in sku_series.tolist():
        raw, base, size, valid = parse_sku_strict(x)
        parsed.append({"raw_sku": raw, "base": base, "size": size, "valid": valid})
    df_parsed = pd.DataFrame(parsed)

st.divider()

# =====================================================
# 两个独立功能：Tabs + 独立按钮
# =====================================================
tab_a, tab_b = st.tabs(["A) 拣货汇总表（Name 排序）", "B) 售出数字列（固定顺序）"])

with tab_a:
    st.subheader("A) 拣货汇总表（按 Name 字母顺序）")
    btn_a = st.button("生成拣货汇总表", type="primary", disabled=(df_parsed is None))

    if btn_a:
        invalid_lines = int((~df_parsed["valid"]).sum())
        if invalid_lines > 0:
            bad_samples = df_parsed.loc[~df_parsed["valid"], "raw_sku"].head(30).tolist()
            st.error("输入中存在无法解析的行（只允许 BASE 或 BASE-S/M/L）。示例：\n" + "\n".join(bad_samples))
            st.stop()

        df_pick, audit = build_picking_summary(df_parsed)

        # 校验：Subtotal 合计 == 输入行数（有效行数）
        if int(df_pick["Subtotal"].sum()) != audit["parsed_lines"]:
            st.error("校验失败：拣货汇总总计 != 输入行数（请检查输入）")
            st.stop()

        c1, c2, c3 = st.columns(3)
        c1.metric("输入行数", int(len(df_parsed)))
        c2.metric("拣货汇总总计", int(df_pick["Subtotal"].sum()))
        c3.metric("产品数（行数）", int(len(df_pick)))

        if audit["unknown_bases"]:
            st.warning("以下 Base SKU 在映射表中未找到（Name=UNKNOWN）：")
            st.code(", ".join(audit["unknown_bases"]))

        st.dataframe(df_pick, use_container_width=True, hide_index=True)
        st.download_button(
            "下载拣货汇总 CSV",
            data=csv_bytes(df_pick, header=True),
            file_name="picking_summary.csv",
            mime="text/csv"
        )

with tab_b:
    st.subheader("B) 售出统计数字列（严格固定 SKU 顺序，无表头）")
    btn_b = st.button("生成售出数字列", type="primary", disabled=(df_parsed is None))

    if btn_b:
        invalid_lines = int((~df_parsed["valid"]).sum())
        if invalid_lines > 0:
            bad_samples = df_parsed.loc[~df_parsed["valid"], "raw_sku"].head(30).tolist()
            st.error("输入中存在无法解析的行（只允许 BASE 或 BASE-S/M/L）。示例：\n" + "\n".join(bad_samples))
            st.stop()

        try:
            df_sold = build_sold_qty_fixed_order(df_parsed)
        except ValueError as e:
            st.error(str(e))
            st.stop()

        st.write(f"固定 SKU 行数：{len(FIXED_SKU_ORDER)}")
        st.write(f"售出合计（S/M/L）：{int(df_sold.sum().iloc[0])}")

        st.dataframe(df_sold, use_container_width=True, hide_index=True)
        st.download_button(
            "下载售出数字列 CSV（无表头）",
            data=csv_bytes(df_sold, header=False),
            file_name="sold_qty_column.csv",
            mime="text/csv"
        )
