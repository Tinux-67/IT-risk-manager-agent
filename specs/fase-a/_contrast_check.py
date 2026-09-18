def rel_lum(hex_color):
    h = hex_color.lstrip('#')
    r, g, b = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    def f(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def ratio(c1, c2):
    l1, l2 = rel_lum(c1), rel_lum(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return round((hi + 0.05) / (lo + 0.05), 2)

pairs = [
    ("#FAFAFA", "#0E1117", "body text on app bg"),
    ("#FAFAFA", "#262730", "body text on secondary bg (cards)"),
    ("#4C9AFF", "#0E1117", "primary on app bg"),
    ("#4C9AFF", "#262730", "primary on card bg"),
    ("#0E1117", "#4C9AFF", "dark text on primary"),
    ("#FFFFFF", "#1A5FB4", "white text on button-primary"),
    ("#FFFFFF", "#0B5394", "white text on button-primary-hover"),
    ("#1D7A46", "#0E1117", "success-fg on bg (large/icon)"),
    ("#FFFFFF", "#1D7A46", "white on success"),
    ("#0E1117", "#2EBD6B", "dark text on success badge bg"),
    ("#B26A00", "#0E1117", "warning-fg on bg"),
    ("#0E1117", "#FFC400", "dark text on warning badge"),
    ("#FFFFFF", "#C62828", "white on danger"),
    ("#0E1117", "#FF6B6B", "dark text on danger badge"),
    ("#FF8A80", "#0E1117", "danger text on bg"),
    ("#A6A6A6", "#0E1117", "muted text on bg"),
    ("#A6A6A6", "#262730", "muted text on card bg"),
    ("#90CAF9", "#0E1117", "info text on bg"),
    ("#0E1117", "#90CAF9", "dark text on info badge"),
    ("#FAFAFA", "#1A5FB4", "focus ring vs bg context"),
    ("#4C9AFF", "#FAFAFA", "(sanity reverse)"),
    ("#0E1117", "#D9D9D9", "dark text on neutral badge"),
]

for fg, bg, ctx in pairs:
    print("%6.2f  %-45s %s on %s" % (ratio(fg, bg), ctx, fg, bg))
