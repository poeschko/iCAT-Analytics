"""
ICDexplorer
A QuadTree implementation to store and access node positions efficiently.

(c) 2011 Jan Poeschko
jan@poeschko.com
"""

import bisect

class QuadTree:
    def __init__(self, xa=0.0, xb=1.0, ya=0.0, yb=1.0, level=0, max_level=5, item_count=1000):
        xa = float(xa)
        xb = float(xb)
        ya = float(ya)
        yb = float(yb)
        assert xa < xb
        assert ya < yb
        assert level <= max_level
        assert item_count >= 1
        self.best_items = []
        self.level = level
        self.max_level = max_level
        self.item_count = item_count
        self.xa = xa
        self.xb = xb
        self.ya = ya
        self.yb = yb
        self.xm = xm = (xa + xb) / 2
        self.ym = ym = (ya + yb) / 2
        self.has_sub = level < max_level
        if self.has_sub:
            sub_level = level + 1
            self.nw = QuadTree(xa, xm, ya, ym, sub_level, item_count=item_count)
            self.ne = QuadTree(xm, xb, ya, ym, sub_level, item_count=item_count)
            self.sw = QuadTree(xa, xm, ym, yb, sub_level, item_count=item_count)
            self.se = QuadTree(xm, xb, ym, yb, sub_level, item_count=item_count)
    
    def insert(self, x, y, item, score):
        if len(self.best_items) < self.item_count or score > self.best_items[0][0]:
            bisect.insort(self.best_items, (score, item, x, y))
            if len(self.best_items) > self.item_count:
                self.best_items = self.best_items[-self.item_count:]
        if self.has_sub:
            if x <= self.xm:
                if y <= self.ym:
                    sub = self.nw
                else:
                    sub = self.sw
            else:
                if y <= self.ym:
                    sub = self.ne
                else:
                    sub = self.se
            sub.insert(x, y, item, score)
            
    def get(self, xa, xb, ya, yb):
        if xa <= self.xa and self.xb <= xb and ya <= self.ya and self.yb <= yb:
            return self.best_items
        elif max(xa, self.xa) <= min(xb, self.xb) and max(ya, self.ya) <= min(yb, self.yb):
            #print (xa, xb, ya, yb)
            if self.has_sub:
                all = []
                for sub in (self.nw, self.ne, self.sw, self.se):
                    all.extend(sub.get(xa, xb, ya, yb))
                    all.sort()
                    all = all[-self.item_count:]
                return all
            else:
                return [(score, item, x, y) for score, item, x, y in self.best_items if xa <= x <= xb and ya <= y <= yb]
        else:
            return []
        
def test():
    qt = QuadTree()
    qt.insert(0.3, 0.3, 'a', 1)
    qt.insert(0.6, 0.3, 'b', 2)
    res = qt.get(0.5, 0.7, 0.2, 0.5)
    assert res[0][1] == 'b'
            