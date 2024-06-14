import xml.etree.ElementTree as ET
import drawpyo
import yaml
import os
from datetime import datetime
import hashlib
import subprocess

class DrawioParser:
    def __init__(self, file_path, yaml_path, env_path, script_dir ,output_path):
        self.file_path = file_path
        self.yaml_path = yaml_path
        self.env_path = env_path
        self.binpkg_dir = script_dir
        self.output_path = output_path
        self.env = {}
        self.id_strMap = {}
        self.id_objMap = {}
        self.edges_map = {}
        self.nodes_map = {}
        self.labeled_edges_map = {}
        self.yaml_data = {}
        self.starting_nodes = []
        self.id_diagMap = {}
        self.style_map = {
            "nodes": {
                "normal": "whiteSpace=wrap;rounded=0;dashed=0;",
                "action_failed": "whiteSpace=wrap;rounded=0;dashed=0;fillColor=#f8cecc;strokeColor=#b85450;",
                "action_pass": "whiteSpace=wrap;rounded=0;dashed=0;fillColor=#d5e8d4;strokeColor=#82b366;",
                "action_more": "whiteSpace=wrap;rounded=0;dashed=0;fillColor=#fff2cc;strokeColor=#d6b656;",
            },
            "edges": {
                "normal": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;entryX=0.5;entryY=0;entryDx=0;entryDy=0;",
            },
            "labels": {
                "normal": "edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];"
            },
        }

        # Create log directories if they don't exist
        self.err_log_dir = os.path.join(self.output_path, "logs/err")
        self.src_log_dir = os.path.join(self.output_path, "logs/src")
        os.makedirs(self.err_log_dir, exist_ok=True)
        os.makedirs(self.src_log_dir, exist_ok=True)

        # Initialize drawio file
        self.diagram_file = drawpyo.File()
        dir_path, file_name = os.path.split(self.file_path)
        self.diagram_file.file_path = dir_path
        self.diagram_file.file_name = file_name

        self._source_shell_file()

    def parse_file(self):
        pass

    def mxGraphModelParse(self):
        with open(self.file_path, "r", encoding="utf-8") as file:
            text_data = file.read()

        drawing = ET.fromstring(text_data)

        for diagram_elem in drawing.findall("./diagram"):
            diagram_name = diagram_elem.attrib.get("name")
            self.id_diagMap[diagram_name] = []
            diagram_root = diagram_elem.find("./mxGraphModel/root")

            for mxcell in diagram_root.findall("./mxCell"):
                mxcell_id = mxcell.attrib.get("id")
                if mxcell_id:
                    self.id_strMap[mxcell_id] = (
                        ET.tostring(mxcell, encoding="unicode"),
                        diagram_name,
                    )
                    self.id_diagMap[diagram_name].append(mxcell_id)

                    if mxcell.attrib.get("edge") == "1":
                        self.edges_map[mxcell_id] = mxcell
                    elif (
                        mxcell.attrib.get("vertex") == "1"
                        and mxcell.attrib.get("parent") == "1"
                    ):
                        self.nodes_map[mxcell_id] = mxcell

        for edge_id, edge in self.edges_map.items():
            for mxcell_str, _ in self.id_strMap.values():
                mxcell_elem = ET.fromstring(mxcell_str)
                if (
                    mxcell_elem.attrib.get("vertex") == "1"
                    and mxcell_elem.attrib.get("connectable") == "0"
                    and mxcell_elem.attrib.get("parent") == edge_id
                ):
                    self.labeled_edges_map[edge_id] = mxcell_elem
                    break
                elif(mxcell_elem.attrib.get("value") != None ):
                    self.labeled_edges_map[edge_id] = mxcell_elem


    def mxobjParse(self):
        objs = []
        id_to_obj = {}

        for mxcell_id, (mxcell_str, diagram_name) in self.id_strMap.items():
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
                style = mxCell.attrib.get("style", self.style_map["nodes"]["normal"])

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
                    "diag_name": diagram_name,
                }
                objs.append(obj)
                id_to_obj[mxcell_id] = obj

        for edge_id, edge in self.edges_map.items():
            source_id = edge.attrib["source"]
            target_id = edge.attrib["target"]
            label = self.labeled_edges_map.get(edge_id, {}).get("value", "")
            style = edge.attrib.get("style", self.style_map["edges"]["normal"])

            edge_obj = {
                "type": "edge",
                "id": edge_id,
                "source": source_id,
                "target": target_id,
                "label": label,
                "style": style,
                "diag_name": self.id_strMap[source_id][1],  # 继承 source 的 diag_name
            }
            objs.append(edge_obj)

        self.id_objMap.update({obj["id"]: obj for obj in objs})
        return objs, id_to_obj

    def chainParse(self, page_name=None):
        objs, id_to_obj = self.mxobjParse()
        sources = set(edge["source"] for edge in objs if edge["type"] == "edge")
        targets = set(edge["target"] for edge in objs if edge["type"] == "edge")

        starting_nodes = [
            node
            for node in objs
            if node["type"] == "node" and node["id"] not in targets and node["id"] in sources
        ]

        if page_name:
            starting_nodes = [node for node in starting_nodes if node["diag_name"] == page_name]

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

        print(node['value'])
        indent = "  " * level
        print(f"{indent}{node['value']} (id: {node['id']})")
        if node["yes"]:
            print(f"{indent}  Yes:")
            self.print_tree(node["yes"], level + 2)
        if node["no"]:
            print(f"{indent}  No:")
            self.print_tree(node["no"], level + 2)

    def actionParse(self):
        with open(self.yaml_path, "r", encoding="utf-8") as file:
            self.yaml_data = yaml.safe_load(file)

        for node in self.starting_nodes:
            self._action_parse_traverse(node)

    def _action_parse_traverse(self, node):
        value = node["value"]
        if value in self.yaml_data:
            action = self.yaml_data[value]
            node["action"] = self._replace_env_vars(action)
        if node["yes"]:
            self._action_parse_traverse(node["yes"])
        if node["no"]:
            self._action_parse_traverse(node["no"])

    def _replace_env_vars(self, action):
        if isinstance(action, dict):
            for key, value in action.items():
                if isinstance(value, list):
                    action[key] = [self._replace_env_vars(item) for item in value]
                elif isinstance(value, str):
                    action[key] = self._replace_env_var(value)
        elif isinstance(action, list):
            return [self._replace_env_vars(item) for item in action]
        elif isinstance(action, str):
            return self._replace_env_var(action)
        return action

    def _replace_env_var(self, value):
        for key, env_value in self.env.items():
            value = value.replace(f"${{{key}}}", env_value)
            value = value.replace(f"${key}", env_value)
        return value

    def _trans2drawObj(self, node):
        return {
            "x": node["x"],
            "y": node["y"],
            "width": node["width"],
            "height": node["height"],
            "value": node["value"],
            "style": node["style"],
        }


    def create_obj(self, type, type_obj):
        if type == "node":
            default_obj = {
                "type": "node",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 80,
                "value": "",
                "style": self.style_map["nodes"]["normal"],
                "yes": None,
                "no": None,
                "action": None,
                "diag_name": None,
                "status": None,
                "link": {},
            }
        elif type == "edge":
            default_obj = {
                "type": "edge",
                "source": "",
                "target": "",
                "label": "",
                "style": self.style_map["edges"]["normal"],
                "diag_name": None,
            }
        else:
            raise ValueError(f"Unknown type: {type}")

        for key in type_obj:
            if key not in default_obj:
                print(f"key:{key}")
                raise ValueError(f"Missing required attribute: {key}")

        obj = {**default_obj, **type_obj}

        obj_id = hashlib.md5(str(obj).encode()).hexdigest()
        while obj_id in self.id_strMap or obj_id in self.id_objMap:
            obj_id = hashlib.md5((str(obj) + str(datetime.now())).encode()).hexdigest()

        obj["id"] = obj_id
        self.id_objMap[obj_id] = obj

    def update_obj(self, obj_id, type_obj):
        if obj_id not in self.id_objMap:
            raise ValueError(f"Object with id {obj_id} does not exist")

        obj = self.id_objMap[obj_id]

        for key, value in type_obj.items():
            if key not in obj:
                raise ValueError(f"Invalid attribute: {key}")
            obj[key] = value

        self.id_objMap[obj_id] = obj

    def add_page(self, page_name):
        page = drawpyo.Page(file=self.diagram_file, name=page_name)

        id_to_draw_obj = {}
        for obj_id, obj in self.id_objMap.items():
            if obj["diag_name"] == page_name:
                if obj["type"] == "node":
                    node_obj = self._trans2drawObj(obj)
                    node = drawpyo.diagram.Object(page=page)
                    node.geometry.x = node_obj["x"]
                    node.geometry.y = node_obj["y"]
                    node.geometry.width = node_obj["width"]
                    node.geometry.height = node_obj["height"]
                    node.value = node_obj["value"]
                    node.apply_style_string(obj["style"])
                    page.add_object(node)
                    id_to_draw_obj[obj_id] = node

        for obj_id, obj in self.id_objMap.items():
            if obj["type"] == "edge" and obj["diag_name"] == page_name:
                source_obj = id_to_draw_obj[obj["source"]]
                target_obj = id_to_draw_obj[obj["target"]]
                edge = drawpyo.diagram.Edge(
                    source=source_obj, target=target_obj, page=page, label=obj["label"]
                )
                edge.apply_style_string(obj["style"])
                page.add_object(edge)

    def draw(self):
        self.diagram_file.write()

    def add_nodelist_diagram(
        self, col_space=100, row_space=50, col_num=3, row_num=None, startpoint=(0, 0)
    ):
        # 删除现有的 nodelist 对象
        self.id_objMap = {key: obj for key, obj in self.id_objMap.items() if obj['diag_name'] != "nodelist"}
        
        self.actionParse()
        for action_name, action_data in self.yaml_data.items():
            node_obj = {
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 80,
                "value": action_name,
                "style": self.style_map["nodes"]["normal"],
                "diag_name": "nodelist",
            }
            self.create_obj("node", node_obj)
        self.checknodes_auto_layout(col_space, row_space, col_num, row_num, startpoint)
        self.add_page("nodelist")

    def checknodes_auto_layout(
        self, col_space=100, row_space=50, col_num=3, row_num=None, startpoint=(0, 0)
    ):
        # 只选择属于 'nodelist' 页的节点
        nodes = [obj for obj in self.id_objMap.values() if obj["type"] == "node" and obj["diag_name"] == "nodelist"]
        if row_num is None:
            row_num = (len(nodes) + col_num - 1) // col_num
        start_x, start_y = startpoint
        for index, node in enumerate(nodes):
            node["x"] = start_x + (index % col_num) * (col_space + node["width"])
            node["y"] = start_y + (index // col_num) * (row_space + node["height"])

    # 添加的 get 函数
    def get_id_strMap(self):
        return self.id_strMap

    def get_id_objMap(self):
        return self.id_objMap

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

    def start_logic(self):
        self.actionParse()
        for node in self.starting_nodes:
            self._execute_action(node)

    def _execute_action(self, node):
        action = node.get("action", {})
        print(action)
        result = True
        log_file = os.path.join(self.err_log_dir, f"{node['value']}.log")

        if os.path.exists(log_file):
            os.remove(log_file)

        if "shell" in action:
            for cmd in action["shell"]:
                cmd = self._replace_env_var(cmd)
                result, output, stdout = self._execute_shell(cmd)
                if not result:
                    with open(log_file, "w") as log:
                        log.write(stdout + "\n" + output)
                    node["style"] = self.style_map["nodes"]["action_failed"]
                    node["status"] = {"action": "fail"}
                    node["link"] = {}
                    node["link"]["err_log"] = log_file
                    break
            if result:
                node["style"] = self.style_map["nodes"]["action_pass"]
                node["status"] = {"action": "pass"}

        elif "mml" in action:
            for mml_obj in action["mml"]:
                mml_cmd = list(mml_obj.keys())[0]
                result, output, stdout = self._execute_mml(mml_cmd)
                if not result:
                    with open(log_file, "w") as log:
                        log.write(stdout + "\n" + output)
                    node["style"] = self.style_map["nodes"]["action_failed"]
                    node["status"] = {"action": "fail"}
                    node["link"] = {}
                    node["link"]["err_log"] = log_file
                    break
            if result:
                node["style"] = self.style_map["nodes"]["action_pass"]
                node["status"] = {"action": "pass"}

        elif "logs" in action:
            for log_path, conditions in action["logs"].items():
                log_path = self._replace_env_var(log_path)
                result = self._check_logs(log_path, conditions)
                if not result:
                    with open(log_file, "w") as log:
                        log.write(f"Log check failed for conditions: {conditions}")
                    node["style"] = self.style_map["nodes"]["action_failed"]
                    node["status"] = {"action": "fail"}
                    node["link"] = {}
                    node["link"]["err_log"] = log_file
                    break
            if result:
                node["style"] = self.style_map["nodes"]["action_pass"]
                node["status"] = {"action": "pass"}

        if node["yes"] and node["status"]["action"] == "pass":
            self._execute_action(node["yes"])
        if node["no"] and node["status"]["action"] == "fail":
            self._execute_action(node["no"])

    def shell(self, cmds):
        try:
            # 执行命令并捕获输出和错误信息
            result = subprocess.run(cmds, shell=True, capture_output=True, text=True)
            # 获取返回码
            return_code = result.returncode
            # 返回输出信息和执行状态
            return result.stdout, result.stderr, return_code
        except Exception as e:
            # 捕获异常并返回错误信息和状态
            return str(e), str(e), -1

    def _execute_shell(self, cmd):
        output, error, status = self.shell(cmd)
        return status == 0, error, output

    def _execute_mml(self, cmd):
        command = f"cd mmlshell && ./mmlshell -c '{cmd}'"
        output, error, status = self.shell(command)
        return status == 0 and self._parse_mml_result(output, cmd), error, output

    def _parse_mml_result(self, result, cmd):
        lines = result.splitlines()
        if len(lines) < 3:
            return False

        keys = lines[0].split(',')
        mml_res = {}

        for line in lines[1:]:
            if not line.strip():
                continue
            values = line.split(',')
            if len(values) != len(keys):
                return False
            mml_res[values[0]] = dict(zip(keys, values))

        expected_conditions = self.yaml_data.get(cmd, [])
        for condition in expected_conditions:
            for key, value in condition.items():
                if mml_res.get(key) != value:
                    return False
        return True

    def _check_logs(self, log_path, conditions):
        if not os.path.exists(log_path):
            return False

        with open(log_path, "r") as file:
            log_content = file.read()

        for condition in conditions:
            if condition not in log_content:
                return False
        return True

    def _source_shell_file(self):
        # Construct the command to source the shell file and print environment variables
        command = f"source {self.env_path} && env"
        result, err ,status = self.shell(command);
        
        env_vars = {}
        for line in result.splitlines():
            key, _, value = line.partition("=")
            env_vars[key] = value
        
        self.env = env_vars
        self.env["binpkg_dir"] = self.binpkg_dir
        print(self.binpkg_dir)
