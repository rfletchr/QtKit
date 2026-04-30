from __future__ import annotations
from .api import Field, Comparison, AndOperator, OrOperator

Node = Comparison | AndOperator | OrOperator


def serialize(node: Node) -> dict:
    if isinstance(node, Comparison):
        return {
            "type": "comparison",
            "field": node.field.name,
            "operator": node.operator,
            "value": node.value,
        }
    if isinstance(node, AndOperator):
        return {"type": "and", "comparisons": [serialize(c) for c in node.comparisons]}
    if isinstance(node, OrOperator):
        return {"type": "or", "comparisons": [serialize(c) for c in node.comparisons]}
    raise ValueError(f"Unknown node type: {type(node)}")


def deserialize(data: dict, fields: list[Field]) -> Node:
    field_map = {f.name: f for f in fields}
    return _node(data, field_map)


def _node(data: dict, field_map: dict[str, Field]) -> Node:
    node_type = data["type"]
    if node_type == "comparison":
        return Comparison(
            field=field_map[data["field"]],
            operator=data["operator"],
            value=data["value"],
        )
    if node_type == "and":
        return AndOperator(
            comparisons=[_node(c, field_map) for c in data["comparisons"]]
        )
    if node_type == "or":
        return OrOperator(
            comparisons=[_node(c, field_map) for c in data["comparisons"]]
        )
    raise ValueError(f"Unknown node type: {node_type!r}")
