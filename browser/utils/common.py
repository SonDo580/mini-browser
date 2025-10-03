def tree_to_list(tree, nodes: list) -> list:
    """Convert a tree structure to a list of nodes. Use in-order DFS."""
    assert hasattr(tree, "children") and isinstance(tree.children, list)
    
    nodes.append(tree)
    for child in tree.children:
        tree_to_list(child, nodes)
    return nodes
