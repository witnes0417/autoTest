import drawpyo
from drawpyo.diagram_types import TreeDiagram

tree = TreeDiagram(
    file_path = './Output',
    file_name = 'test.drawio',
)

from drawpyo.diagram_types import NodeObject

from N2G import drawio_diagram
import drawpyo

# 读取并解析 Draw.io 文件
file_path = "Output/test1.drawio"
converter = drawio_diagram()
converter.from_file(file_path)

# 创建 Drawpyo 文件和页面对象
diagram_file = drawpyo.File()
page = drawpyo.Page(file=diagram_file)

# 获取解析后的页面数据
parsed_data = converter.drawing

# 创建一个字典以便映射节点ID到 Drawpyo 对象
id_to_obj = {}

# 提取并添加节点
for diagram_elem in parsed_data.findall("./diagram"):
    diagram_root = diagram_elem.find("./mxGraphModel/root")

    for object_tag in diagram_root.findall("./object"):
        object_id = object_tag.attrib["id"]
        mxCell = object_tag.find("./mxCell")
        
        # 如果是节点
        if "vertex" in mxCell.attrib and mxCell.attrib.get("vertex") == "1":
            mxGeometry = mxCell.find("./mxGeometry")
            x = int(mxGeometry.attrib.get("x", 0))
            y = int(mxGeometry.attrib.get("y", 0))
            width = int(mxGeometry.attrib.get("width", 100))
            height = int(mxGeometry.attrib.get("height", 80))
            value = object_tag.attrib.get("label", "")
            style = mxCell.attrib.get("style", "")
            
            obj = drawpyo.diagram.Object(page=page)
            obj.geometry.x = x
            obj.geometry.y = y
            obj.geometry.width = width
            obj.geometry.height = height
            obj.value = value
            page.add_object(obj)
            id_to_obj[object_id] = obj

# 提取并添加边
for diagram_elem in parsed_data.findall("./diagram"):
    diagram_root = diagram_elem.find("./mxGraphModel/root")

    for object_tag in diagram_root.findall("./object"):
        mxCell = object_tag.find("./mxCell")
        
        # 如果是边
        if "source" in mxCell.attrib and "target" in mxCell.attrib:
            source_id = mxCell.attrib["source"]
            target_id = mxCell.attrib["target"]
            source_obj = id_to_obj[source_id]
            target_obj = id_to_obj[target_id]
            label = mxCell.attrib.get("value", "")
            style = mxCell.attrib.get("style", "")
            edge_obj = drawpyo.diagram.Edge(source=source_obj, target=target_obj, page=page, label=label)
            page.add_object(edge_obj)

# 保存文件
diagram_file.file_path = "Output/diagram.drawio"
diagram_file.write()



# # 创建文件对象
# file = drawpyo.File()
# file.file_path = "./Output"
# file.file_name = "test1.drawio"

# # 添加页面
# page = drawpyo.Page(file=file)

# # 创建第一个节点
# node1 = drawpyo.diagram.Object(page=page)
# node1.value = "Node 1"
# node1.geometry.x = 100
# node1.geometry.y = 100

# # 创建第二个节点
# node2 = drawpyo.diagram.Object(page=page)
# node2.value = "Node 2"
# node2.geometry.x = 300
# node2.geometry.y = 100

# # 创建第三个节点
# node3 = drawpyo.diagram.Object(page=page)
# node3.value = "Node 3"
# node3.geometry.x = 200
# node3.geometry.y = 300

# # 连接节点 1 和节点 2
# edge1 = drawpyo.diagram.Edge(source=node1, target=node2, page=page)
# edge1.strokeColor = "#000000"  # 黑色线条

# # 连接节点 2 和节点 3
# edge2 = drawpyo.diagram.Edge(source=node2, target=node3, page=page)
# edge2.strokeColor = "#000000"  # 黑色线条

# # 连接节点 3 和节点 1
# edge3 = drawpyo.diagram.Edge(source=node3, target=node1, page=page)
# edge3.strokeColor = "#000000"  # 黑色线条


# file.write()


# # Top object
# grinders = NodeObject(tree=tree, value="Appliances for Grinding Coffee", base_style="rounded rectangle")

# # Main categories
# blade_grinders = NodeObject(tree=tree, value="Blade Grinders", parent=grinders)
# burr_grinders = NodeObject(tree=tree, value="Burr Grinders", parent=grinders)
# blunt_objects = NodeObject(tree=tree, value="Blunt Objects", parent=grinders)

# # Other
# elec_blade = NodeObject(tree=tree, value="Electric Blade Grinder", parent=blade_grinders)
# mnp = NodeObject(tree=tree, value="Mortar and Pestle", parent=blunt_objects)

# # Conical Burrs
# conical = NodeObject(tree=tree, value="Conical Burrs", parent=burr_grinders)
# elec_conical = NodeObject(tree=tree, value="Electric", parent=conical)
# manual_conical = NodeObject(tree=tree, value="Manual", parent=conical) 

# tree.auto_layout()
# tree.write()


# # 读取和解析 没有压缩的 mxGraphModel 文件
# tree = ET.parse('Output/test1.drawio')
# root = tree.getroot()

# # 遍历所有 mxCell 元素
# for cell in root.findall('.//mxCell'):
#     cell_id = cell.get('id')
#     value = cell.get('value')
#     style = cell.get('style')
#     print(f'ID: {cell_id}, Value: {value}, Style: {style}')
