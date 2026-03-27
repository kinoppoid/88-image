"""
LZE圧縮/展開モジュール
Original: Copyright (C)1995,2008 GORRY.
C# Port: Kei Moroboshi(@kmoroboshi), Oct/2018-Jul/2020
Python Port: 2026

BZCOMPATIBLE=True, SPEED=True でビルドされた lze.exe と互換。
"""

N   = 16384   # 辞書バッファサイズ
F   = 256     # 最大一致長
IDX = 8192    # ハッシュテーブルサイズ (SPEED=True)
NIL = -1


def encode(data: bytes) -> bytes:
    """LZE圧縮。4バイトの元サイズヘッダ付きで返す。"""

    indata = data
    inpos  = [0]

    def read_byte():
        if inpos[0] >= len(indata):
            return -1
        v = indata[inpos[0]]
        inpos[0] += 1
        return v

    out = bytearray()

    # 辞書バッファ・木
    text = bytearray((N + F) * 256)
    son  = [NIL] * (N + 1 + IDX)
    dad  = [NIL] * (N + 1 + IDX)
    same = [0]   * N

    # 共有状態
    st = dict(
        matchpos=0, matchlen=0,
        noder=NIL,  nodeo=NIL,
        samecount=0,
        flags=0, flagscnt=0, codeptr=1, code2size=0,
    )
    code  = bytearray(256)
    code2 = bytearray(4)

    # ------------------------------------------------------------------ tree

    def init_tree():
        for i in range(N + 1 + IDX):
            son[i] = NIL
            dad[i] = NIL

    def insert_node(r):
        sc = st['samecount']
        if sc > 0:
            same[r] = sc
            st['samecount'] = sc - 1
        else:
            c  = text[r]
            pr = r + 1
            sc = 0
            for sc in range(F - 1):
                if text[pr] != c:
                    break
                pr += 1
            else:
                sc = F - 1
            same[r] = sc
            st['samecount'] = sc - 1

        k = (text[r] << 5) ^ text[r + 1]
        o = son[N + 1 + k]
        son[N + 1 + k] = r
        st['nodeo'] = o
        st['noder'] = r
        if o < 0:
            dad[N + 1 + k] = r
            return
        son[r] = o
        dad[o] = r
        dad[r] = NIL

    def delete_node(p):
        k  = (text[p] << 5) ^ text[p + 1]
        ri = N + 1 + k
        q  = dad[ri]
        while True:
            if q < 0:
                return
            if p == q:
                dq = dad[q]
                if dq < 0:
                    son[N + 1 + k] = son[q]
                else:
                    son[dq] = son[q]
                dad[ri] = dq
                dad[q]  = NIL
                return
            ri = q
            q  = dad[q]

    def get_node():
        mlen = 0
        o = st['nodeo']
        r = st['noder']
        if o < 0:
            return mlen
        n = same[r]

        while o >= 0:
            m = (r - o) & (N - 1)
            if m > 8192:
                return mlen

            # 現在の一致長の末尾から逆向きに最大4バイト先読みチェック（高速化）
            i  = mlen
            pi = r + i + 1
            qi = o + i + 1
            skip = False
            for _ in range(4):
                if not skip and i > 0:
                    i -= 1; pi -= 1; qi -= 1
                    if text[pi] != text[qi]:
                        o = son[o]; skip = True
            if skip:
                continue

            si = n
            if si > same[o]:
                si = same[o]
            pi = r + si
            qi = o + si
            if text[pi] != text[qi]:
                o = son[o]
                continue
            pi += 1; qi += 1
            i = si

            while i < F:
                i += 1
                if text[pi] != text[qi]: break
                pi += 1; qi += 1
                i += 1
                if text[pi] != text[qi]: break
                pi += 1; qi += 1
                i += 1
                if text[pi] != text[qi]: break
                pi += 1; qi += 1
                i += 1
                if text[pi] != text[qi]: break
                pi += 1; qi += 1

            if i > F:
                i = F
            if mlen < i:
                st['matchpos'] = m
                mlen = i
                if i >= F:
                    return mlen

            o = son[o]

        return mlen

    # ------------------------------------------------------------------ encoder

    def putencode(r_pos):
        fl   = st['flags'];    fc   = st['flagscnt']
        mlen = st['matchlen']; mpos = st['matchpos']
        size = 0

        if mlen < 2:
            st['matchlen'] = 1
            fl = (fl << 1) | 1;  fc += 1
            code2[0] = text[r_pos];  st['code2size'] = 1
        elif mlen < 6 and mpos < 257:
            fl = (fl << 4) | (mlen - 2);  fc += 4
            code2[0] = (256 - mpos) & 0xFF;  st['code2size'] = 1
        elif mlen > 9:
            fl = (fl << 2) | 1;  fc += 2
            mp = 8192 - mpos
            code2[0] = (mp >> 5) & 0xFF
            code2[1] = (mp << 3) & 0xFF
            code2[2] = (mlen - 1) & 0xFF;  st['code2size'] = 3
        elif mlen > 2:
            fl = (fl << 2) | 1;  fc += 2
            mp = 8192 - mpos
            code2[0] = (mp >> 5) & 0xFF
            code2[1] = ((mp << 3) | (mlen - 2)) & 0xFF;  st['code2size'] = 2
        else:
            # mlen==2 だが短距離条件不成立 → リテラルに格下げ
            st['matchlen'] = 1
            fl = (fl << 1) | 1;  fc += 1
            code2[0] = text[r_pos];  st['code2size'] = 1

        if fc > 8:
            fc -= 8
            code[0] = (fl >> fc) & 0xFF
            cp = st['codeptr']
            for i in range(cp):
                out.append(code[i])
            size += cp
            st['codeptr'] = 1
            fl &= (0xFF >> (8 - fc))

        cp  = st['codeptr']
        c2s = st['code2size']
        for i in range(c2s):
            code[cp + i] = code2[i]
        st['codeptr'] = cp + c2s

        st['flags']    = fl
        st['flagscnt'] = fc
        return size

    def finish_putencode():
        fl = (st['flags'] << 2) | 1
        fc = st['flagscnt'] + 2
        cp = st['codeptr']

        if fc > 8:
            fc -= 8
            code[0] = (fl >> fc) & 0xFF
            for i in range(cp):
                out.append(code[i])
            cp = 1
            fl &= (0xFF >> (8 - fc))

        # 終端マーカー: 3バイト 0x00
        code[cp] = 0; code[cp+1] = 0; code[cp+2] = 0
        cp += 3

        if fc > 0:
            code[0] = (fl << (8 - fc)) & 0xFF
        if cp > 1:
            for i in range(cp):
                out.append(code[i])

    # ------------------------------------------------------------------ main

    size_val = len(data)
    hdr = bytes([(size_val >> 24) & 0xFF, (size_val >> 16) & 0xFF,
                 (size_val >>  8) & 0xFF,  size_val        & 0xFF])

    init_tree()

    s = 0
    r = N - F
    for i in range(r):
        text[i] = 0

    # 最初のFバイトを読み込む
    i = 0
    for i in range(F):
        c = read_byte()
        if c < 0:
            break
        text[r + i] = c
    else:
        i = F

    llen = i
    if llen == 0:
        return hdr

    # BZCOMPATIBLE: 先頭1バイトをそのまま出力
    insert_node(r)
    out.append(text[r])
    c = read_byte()
    if c >= 0:
        text[s] = c
        if s < F - 1:
            text[s + N] = c
        s = (s + 1) & (N - 1)
        r = (r + 1) & (N - 1)
    else:
        s = (s + 1) & (N - 1)
        r = (r + 1) & (N - 1)
        llen -= 1
        if llen == 0:
            finish_putencode()
            return hdr + bytes(out)

    insert_node(r)
    ok_del = False

    while llen > 0:
        st['matchlen'] = get_node()
        if st['matchlen'] > llen:
            st['matchlen'] = llen
        putencode(r)
        st['matchpos'] = N + 1
        ml = st['matchlen']

        # mlen バイト分、新しいデータを読んで辞書を更新
        i = 0
        while i < ml:
            c = read_byte()
            if c < 0:
                break
            if ok_del:
                delete_node(s)
            elif s == N - F - 1:
                ok_del = True
            text[s] = c
            if s < F - 1:
                text[s + N] = c
            s = (s + 1) & (N - 1)
            r = (r + 1) & (N - 1)
            insert_node(r)
            i += 1

        # EOF後の残り分を空送り（辞書更新のみ、llen をカウントダウン）
        while i < ml:
            if ok_del:
                delete_node(s)
            elif s == N - F - 1:
                ok_del = True
            s = (s + 1) & (N - 1)
            r = (r + 1) & (N - 1)
            llen -= 1
            if llen != 0:
                insert_node(r)
            i += 1

    finish_putencode()
    return hdr + bytes(out)


def decode(data: bytes) -> bytes:
    """LZE展開。4バイトのサイズヘッダを除いた元データを返す。"""

    indata = data
    inpos  = [4]  # 先頭4バイトはサイズヘッダ

    def read_byte():
        if inpos[0] >= len(indata):
            return -1
        v = indata[inpos[0]]
        inpos[0] += 1
        return v

    out  = bytearray()
    text = bytearray(N)

    r = N - F

    # BZCOMPATIBLE: 先頭1バイトをそのまま出力
    c = read_byte()
    if c < 0:
        return bytes(out)
    out.append(c)
    text[r] = c
    r = (r + 1) & (N - 1)

    flags    = 0
    flagscnt = 0

    def get_bit():
        nonlocal flags, flagscnt
        flagscnt -= 1
        if flagscnt < 0:
            c = read_byte()
            if c < 0:
                return -1
            flags    = c
            flagscnt = 7
        bit = (flags >> 7) & 1
        flags = (flags << 1) & 0xFF
        return bit

    while True:
        bit = get_bit()
        if bit < 0:
            break

        if bit:
            # 1: リテラル
            c = read_byte()
            if c < 0:
                break
            out.append(c)
            text[r] = c
            r = (r + 1) & (N - 1)
        else:
            bit = get_bit()
            if bit < 0:
                break

            if bit:
                # 01: 遠距離一致（2〜3バイト）
                i = read_byte()
                if i < 0:
                    break
                j = read_byte()
                if j < 0:
                    break
                u = (i << 8) | j
                jj = u & 7
                u >>= 3
                if jj == 0:
                    jj = read_byte()
                    if jj < 0:
                        break
                    if jj == 0:
                        break   # 終端マーカー
                    jj += 1
                else:
                    jj += 2
                ii = (r - (8192 - u)) & (N - 1)
            else:
                # 00xx: 近距離一致（1バイト）
                b1 = get_bit()
                if b1 < 0:
                    break
                b2 = get_bit()
                if b2 < 0:
                    break
                jj = (b1 << 1 | b2) + 2
                i  = read_byte()
                if i < 0:
                    break
                ii = (r - (256 - i)) & (N - 1)

            for k in range(jj):
                c = text[(ii + k) & (N - 1)]
                out.append(c)
                text[r] = c
                r = (r + 1) & (N - 1)

    return bytes(out)


if __name__ == '__main__':
    import sys, os

    if len(sys.argv) != 4 or sys.argv[1].lower() not in ('e', 'd'):
        print('Usage: python3 lze.py e infile outfile')
        print('       python3 lze.py d infile outfile')
        sys.exit(1)

    mode, src, dst = sys.argv[1].lower(), sys.argv[2], sys.argv[3]
    data = open(src, 'rb').read()

    if mode == 'e':
        result = encode(data)
        print(f'In : {len(data)} bytes')
        print(f'Out: {len(result)} bytes')
    else:
        result = decode(data)
        print(f'Out: {len(result)} bytes')

    open(dst, 'wb').write(result)
