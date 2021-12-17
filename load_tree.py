from binary_tree import BST
import json

with open('treeFile.txt') as file_obj:
    tree = BST.loadTree(json.load(file_obj))

print(tree.inorder([]))