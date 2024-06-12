import xml.etree.ElementTree as ET
import drawpyo
import yaml
import os
from datetime import datetime


class DrawioParser:
    def __init__(self, file_path, yaml_path, output_path):
        self.file_path = file_path
        self.yaml_path = yaml_path
        self.output_path = output_path
        self.id_map = {}
        self.edges_map = {}
        self.nodes_map = {}
        self.labeled_edges_map = {}
        self.yaml_data = {}
        self.starting_nodes = []
        self.style_map = {
            "nodes": {
                "normal": "whiteSpace=wrap;rounded=0;dashed=0;",
                "check_failed": "whiteSpace=wrap;rounded=0;dashed=0;fillColor=#f8cecc;strokeColor=#b85450;",
                "check_pass": "whiteSpace=wrap;rounded=0;dashed=0;fillColor=#d5e8d4;strokeColor=#82b366;",
                "check_more": "whiteSpace=wrap;rounded=0;dashed=0;fillColor=#fff2cc;strokeColor=#d6b656;",
            },
            "edges": "edgeStyle=orthogonalEdgeStyle;rounded=0;",
            "labels": "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;",
        }

    def parse_file(self):
        pass

    def mxGraphModelParse(self):
        with open(self.file_path, "r", encoding="utf-8") as file:
            text_data = file.read()

        drawing = ET.fromstring(text_data)

        for diagram_elem in drawing.findall("./diagram"):
            diagram_root = diagram_elem.find("./mxGraphModel/root")

            for mxcell in diagram_root.findall("./mxCell"):
                mxcell_id = mxcell.attrib.get("id")
                if mxcell_id:
                    self.id_map[mxcell_id] = ET.tostring(mxcell, encoding="unicode")

                    if mxcell.attrib.get("edge") == "1":
                        self.edges_map[mxcell_id] = mxcell
                    elif (
                        mxcell.attrib.get("vertex") == "1"
                        and mxcell.attrib.get("parent") == "1"
                    ):
                        self.nodes_map[mxcell_id] = mxcell

        for edge_id, edge in self.edges_map.items():
            for mxcell_str in self.id_map.values():
                mxcell_elem = ET.fromstring(mxcell_str)
                if (
                    mxcell_elem.attrib.get("vertex") == "1"
                    and mxcell_elem.attrib.get("connectable") == "0"
                    and mxcell_elem.attrib.get("parent") == edge_id
                ):
                    self.labeled_edges_map[edge_id] = mxcell_elem
                    break

    def mxobjParse(self):
        objs = []
        id_to_obj = {}

        for mxcell_id, mxcell_str in self.id_map.items():
            mxCell = ET.fromstring(mxcell_str)

            if (
                mxCell.attrib.get("vertex") == "1"
                and mxCell.attrib.get("parent") == "1"
            ):
                mxGeometry = mxCell.find("./mxGeometry")
                x = int(mxGeometry.attrib.get("x", 0))
                y = int(mxGeometry.attrib.get("y", 0))
                width = int(mxGeometry.attrib.get("width", 100))
                height = int(mxGeometry.attrib.get("height", 80))
                value = mxCell.attrib.get("value", "")
                style = mxCell.attrib.get("style", "")

                obj = {
                    "type": "node",
                    "id": mxcell_id,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "value": value,
                    "style": style,
                    "yes": None,
                    "no": None,
                }
                objs.append(obj)
                id_to_obj[mxcell_id] = obj

        for edge_id, edge in self.edges_map.items():
            source_id = edge.attrib["source"]
            target_id = edge.attrib["target"]
            label = self.labeled_edges_map.get(edge_id, {}).get("value", "")
            style = edge.attrib.get("style", "")

            edge_obj = {
                "type": "edge",
                "id": edge_id,
                "source": source_id,
                "target": target_id,
                "label": label,
                "style": style,
            }
            objs.append(edge_obj)

        return objs, id_to_obj

    def chainParse(self):
        objs, id_to_obj = self.mxobjParse()
        sources = set(edge["source"] for edge in objs if edge["type"] == "edge")
        targets = set(edge["target"] for edge in objs if edge["type"] == "edge")
        starting_nodes = [
            node
            for node in objs
            if node["type"] == "node" and node["id"] not in targets
        ]

        def traverse(node):
            current_node = node
            edges = [
                edge
                for edge in objs
                if edge["type"] == "edge" and edge["source"] == current_node["id"]
            ]
            for edge in edges:
                next_node = id_to_obj.get(edge["target"])
                if not next_node:
                    continue

                label = edge["label"].strip().lower()
                if label in ["yes", "y"]:
                    current_node["yes"] = next_node
                elif label in ["no", "n"]:
                    current_node["no"] = next_node

                traverse(next_node)

        for start_node in starting_nodes:
            traverse(start_node)

        self.starting_nodes = starting_nodes

    def print_tree(self, node=None, level=0):
        if node is None:
            for root in self.starting_nodes:
                self.print_tree(root)
            return

        indent = "  " * level
        print(f"{indent}{node['value']} (id: {node['id']})")
        if node["yes"]:
            print(f"{indent}  Yes:")
            self.print_tree(node["yes"], level + 2)
        if node["no"]:
            print(f"{indent}  No:")
            self.print_tree(node["no"], level + 2)

    def checkNodesParse(self):
        with open(self.yaml_path, "r", encoding="utf-8") as file:
            self.yaml_data = yaml.safe_load(file)

        for node in self.starting_nodes:
            self._check_node(node)

    def _check_node(self, node):
        value = node["value"]
        if value in self.yaml_data:
            node["check"] = self.yaml_data[value]
            if node["check"] == "failed":
                node["style"] = self.style_map["nodes"]["check_failed"]
            elif node["check"] == "pass":
                node["style"] = self.style_map["nodes"]["check_pass"]
            else:
                node["style"] = self.style_map["nodes"]["check_more"]
        if node["yes"]:
            self._check_node(node["yes"])
        if node["no"]:
            self._check_node(node["no"])

    def create_node(self, node):
        return {
            "x": node["x"],
            "y": node["y"],
            "width": node["width"],
            "height": node["height"],
            "value": node["value"],
            "style": node["style"],
        }

    def update_nodes(self):
        for node in self.nodes_map.values():
            node_obj = self.create_node(node)
            self.create_drawpyo_node(node_obj)

    def create_drawpyo_node(self, node_obj):
        graph = drawpyo.Graph()
        node = graph.add_node(
            value=node_obj["value"],
            x=node_obj["x"],
            y=node_obj["y"],
            width=node_obj["width"],
            height=node_obj["height"],
            style=node_obj["style"],
        )

    def draw_page(self):
        graph = drawpyo.Graph()
        for node in self.nodes_map.values():
            node_obj = self.create_node(node)
            self.create_drawpyo_node(node_obj)

        output_file = os.path.join(
            self.output_path,
            f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.drawio",
        )
        graph.save(output_file)
        print(f"Graph saved to {output_file}")

    # 添加的 get 函数
    def get_id_map(self):
        return self.id_map

    def get_edges_map(self):
        return self.edges_map

    def get_nodes_map(self):
        return self.nodes_map

    def get_labeled_edges_map(self):
        return self.labeled_edges_map

    def get_yaml_data(self):
        return self.yaml_data

    def get_starting_nodes(self):
        return self.starting_nodes


# 使用示例
file_path = "Output/test1.drawio"
yaml_path = "checknodes.yaml"
output_path = "Output/"
parser = DrawioParser(file_path, yaml_path, output_path)
parser.mxGraphModelParse()
parser.chainParse()
parser.checkNodesParse()
parser.print_tree()
parser.update_nodes()
parser.draw_page()

# 获取解析后的结果
id_map = parser.get_id_map()
edges_map = parser.get_edges_map()
nodes_map = parser.get_nodes_map()
labeled_edges_map = parser.get_labeled_edges_map()
yaml_data = parser.get_yaml_data()
starting_nodes = parser.get_starting_nodes()

print("ID Map:", id_map)
print("Edges Map:", edges_map)
print("Nodes Map:", nodes_map)
print("Labeled Edges Map:", labeled_edges_map)
print("YAML Data:", yaml_data)
print("Starting Nodes:", starting_nodes)
