"""
artist_parser — 從演唱會標題推斷主要藝人名稱。

使用方式：
    from app.services.artist_parser import parse_artist
    artist = parse_artist("周杰倫 2026 嘉年華世界巡迴演唱會 台北站")  # "周杰倫"
"""
import re

# 已知藝人清單（支援中英文別名）
_KNOWN_ARTISTS: list[tuple[str, list[str]]] = [
    # 台灣
    ("周杰倫",      ["周杰倫", "jay chou", "jay-chou"]),
    ("五月天",      ["五月天", "mayday"]),
    ("張惠妹",      ["張惠妹", "a-mei", "amei"]),
    ("蔡依林",      ["蔡依林", "jolin tsai", "jolin"]),
    ("林俊傑",      ["林俊傑", "jj lin"]),
    ("陳奕迅",      ["陳奕迅", "eason chan", "eason"]),
    ("鄧紫棋",      ["鄧紫棋", "g.e.m", "g.e.m.", "gem"]),
    ("韋禮安",      ["韋禮安", "william wei"]),
    ("告五人",      ["告五人", "accusefive"]),
    ("草東沒有派對", ["草東沒有派對", "no party for cao dong"]),
    ("盧廣仲",      ["盧廣仲", "crowd lu"]),
    ("滅火器",      ["滅火器", "fire ex"]),
    ("茄子蛋",      ["茄子蛋", "egg planthead"]),
    ("宇宙人",      ["宇宙人", "cosmospeople"]),
    ("老王樂隊",    ["老王樂隊", "wang band"]),
    ("旺福",        ["旺福", "wonfu"]),
    ("拍謝少年",    ["拍謝少年", "sorry youth"]),
    ("SUNSET ROLLERCOASTER", ["sunset rollercoaster", "落日飛車"]),
    ("落日飛車",    ["落日飛車", "sunset rollercoaster"]),
    ("魏如萱",      ["魏如萱", "waa wei"]),
    ("陳珊妮",      ["陳珊妮", "sandee chan"]),
    ("許富凱",      ["許富凱"]),
    ("玖壹壹",      ["玖壹壹", "911"]),
    ("動力火車",    ["動力火車", "power station"]),
    ("伍佰",        ["伍佰", "wu bai"]),
    # 日本
    ("YOASOBI",     ["yoasobi"]),
    ("King & Prince", ["king & prince", "king and prince"]),
    ("Official髭男dism", ["official髭男dism", "official hige dandism", "髭男"]),
    ("米津玄師",    ["米津玄師", "kenshi yonezu", "yonezu"]),
    ("あいみょん",   ["あいみょん", "aimyon"]),
    ("back number", ["back number"]),
    ("sumika",      ["sumika"]),
    ("Charlie Puth", ["charlie puth"]),
    ("Eve",         ["eve"]),
    ("indigo la End", ["indigo la end"]),
    ("ずっと真夜中でいいのに", ["ずっと真夜中でいいのに", "zutomayo"]),
    ("SUZUKI AIRI", ["suzuki airi", "鈴木愛理"]),
    ("yutori",      ["yutori"]),
    # 韓國
    ("BTS",         ["bts", "방탄소년단"]),
    ("BLACKPINK",   ["blackpink"]),
    ("aespa",       ["aespa"]),
    ("IVE",         ["ive"]),
    ("NewJeans",    ["newjeans", "new jeans"]),
    ("SEVENTEEN",   ["seventeen", "세븐틴"]),
    ("STRAY KIDS",  ["stray kids", "스트레이키즈"]),
    ("NCT",         ["nct 127", "nct dream", "nct"]),
    ("EXO",         ["exo"]),
    ("GOT7",        ["got7"]),
    # 歐美
    ("Taylor Swift", ["taylor swift"]),
    ("Ed Sheeran",  ["ed sheeran"]),
    ("Coldplay",    ["coldplay"]),
    ("The Weeknd",  ["the weeknd", "weeknd"]),
    ("Bruno Mars",  ["bruno mars"]),
]


def parse_artist(title: str) -> str:
    """
    從活動標題推斷主要藝人名稱。
    先比對已知藝人清單，找不到則用標題前段（去除年份、巡迴、演唱會等關鍵字）。
    """
    if not title:
        return "未知藝人"

    lower = title.lower()

    # 比對已知藝人（短名稱用單字邊界避免誤匹配）
    for canonical, aliases in _KNOWN_ARTISTS:
        for alias in aliases:
            al = alias.lower()
            # 短於 4 字元的英文詞需用單字邊界（避免 "ive" 匹配 "live"）
            if len(al) <= 4 and re.match(r'^[a-z0-9]+$', al):
                pattern = r'(?<![a-z0-9])' + re.escape(al) + r'(?![a-z0-9])'
                if re.search(pattern, lower):
                    return canonical
            else:
                if al in lower:
                    return canonical

    # 清理標題取前段作為藝人名稱
    cleaned = _strip_concert_suffix(title)
    if cleaned and len(cleaned) >= 2:
        return cleaned

    return title[:20].strip()


def _strip_concert_suffix(title: str) -> str:
    """
    移除常見的演唱會後綴，回傳藝人部分。
    範例：
        "周杰倫 2026 嘉年華世界巡迴演唱會 台北站" → "周杰倫"
        "五月天 OAOA 世界巡迴演唱會" → "五月天"
    """
    # 移除站別（台北站、高雄站 etc.）
    title = re.sub(r'[\s\-_]+(台北|台中|高雄|台南|桃園|新北|宜蘭|花蓮|台東)站.*$', '', title, flags=re.IGNORECASE)
    # 移除演唱會 / 音樂會 / 巡迴 / Live 等後綴
    title = re.sub(
        r'[\s\-_]+(世界巡迴|巡迴演唱會|演唱會|音樂會|LIVE TOUR|LIVE CONCERT|CONCERT TOUR|'
        r'CONCERT|TOUR|LIVE|嘉年華|慶功|跨年|大型|戶外|室內|線上)',
        '', title, flags=re.IGNORECASE
    )
    # 移除年份
    title = re.sub(r'\s*20\d{2}\s*', ' ', title).strip()
    # 取第一個空白前的詞作藝人名
    parts = title.split()
    if parts:
        return parts[0].strip()
    return title.strip()
