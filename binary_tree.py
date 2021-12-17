class BST:
    def __init__(self, val=None):
        self.left = None
        self.right = None
        self.val = val

    def insert(self, val):
        if not self.val:
            self.val = val
            return

        if self.val == val:
            return

        if val < self.val:
            if self.left:
                self.left.insert(val)
                return
            self.left = BST(val)
            return

        if self.right:
            self.right.insert(val)
            return
        self.right = BST(val)

    def jsonable(self):
        return {
            "val" : self.val, 
            "left" : self.left.jsonable() if self.left else None,
            "right" : self.right.jsonable() if self.right else None,
        }

    @classmethod
    def loadTree(cls, dic):
        obj = cls(dic["val"])
        if 'left' in dic.keys() and dic["left"] is not None:
            obj.left = cls.loadTree(dic["left"])
        if 'right' in dic.keys() and dic["right"] is not None:
            obj.right = cls.loadTree(dic["right"])
        return obj

    def inorder(self, vals):
        if self.left is not None:
            self.left.inorder(vals)
        if self.val is not None:
            vals.append(self.val)
        if self.right is not None:
            self.right.inorder(vals)
        return vals