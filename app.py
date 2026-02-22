import json
import viktor as vkt
from io import BytesIO
from pathlib import Path
 
 
def create_frame_data(length, height):
    nodes = {
        1:{"node_id": 1, "x": 0, "y": 0, "z": 0},
        2:{"node_id": 2, "x": 0, "y": length, "z": 0},
        3:{"node_id": 3, "x": 0, "y": 0, "z": height},
        4:{"node_id": 4, "x": 0, "y": length, "z": height},
        5:{"node_id": 5, "x": length, "y": 0, "z": 0},
        6:{"node_id": 6, "x": length, "y": length, "z": 0},
        7:{"node_id": 7, "x": length, "y": 0, "z": height},
        8:{"node_id": 8, "x": length, "y": length, "z": height},
    }
    lines = {
        1:{"line_id": 1, "node_i": 1, "node_j": 3},
        2:{"line_id": 2, "node_i": 2, "node_j": 4},
        3:{"line_id": 3, "node_i": 3, "node_j": 4},
        4:{"line_id": 4, "node_i": 6, "node_j": 8},
        5:{"line_id": 5, "node_i": 5, "node_j": 7},
        6:{"line_id": 6, "node_i": 3, "node_j": 7},
        7:{"line_id": 7, "node_i": 4, "node_j": 8},
        8:{"line_id": 8, "node_i": 7, "node_j": 8},
    }
    return nodes, lines
 
class Parametrization(vkt.Parametrization):
    intro = vkt.Text(
        "# ETABS Base Reaction App"
        "\n\n Please fill in the following parameters:"
    )
    frame_length = vkt.NumberField("Frame Length", min=100, default=4000, suffix="mm")
    frame_height = vkt.NumberField("Frame Height", min=100, default=4000, suffix="mm")
 
 
class Controller(vkt.Controller):
    parametrization = Parametrization
    @vkt.GeometryView("3D Model", duration_guess=1, x_axis_to_right=True)
    def create_render(self, params, **kwargs):
        nodes, lines = create_frame_data(length=params.frame_length, height=params.frame_height)
        sections_group = []
        for line_id, dict_vals in lines.items():
            node_id_i = dict_vals["node_i"]
            node_id_j = dict_vals["node_j"]
 
            node_i = nodes[node_id_i]
            node_j = nodes[node_id_j]
 
            point_i = vkt.Point(node_i["x"], node_i["y"], node_i["z"])
            point_j = vkt.Point(node_j["x"], node_j["y"], node_j["z"])
            line_k = vkt.Line(point_i, point_j)
 
            section_k = vkt.RectangularExtrusion(300, 300, line_k, identifier=str(line_id))
            sections_group.append(section_k)
        return vkt.GeometryResult(geometry=sections_group)
    @vkt.TableView("Base Reactions",duration_guess=10, update_label="Run ETABS analysis")
    def run_etabs(self, params, **kwargs):
        nodes, lines = create_frame_data(length=params.frame_length, height= params.frame_height)
        input_json = json.dumps([nodes, lines])
        script_path = Path(__file__).parent / "run_etabs_model.py"
 
        files = [("inputs.json", BytesIO(bytes(input_json, 'utf8')))]
        etabs_analysis = vkt.etabs.ETABSAnalysis(
            script=vkt.File.from_path(script_path), files=files, output_filenames=["output.json"]
        )
        etabs_analysis.execute(timeout=300)
 
        output_file = etabs_analysis.get_output_file("output.json")
        reactions = json.loads(output_file.getvalue())
        data = []
        for reaction in reactions:
            data.append([
                reaction.get("Node", 0),
                reaction.get("LoadCase", "Dead"),
                round(reaction.get("U1", 0), 0),   
                round(reaction.get("U2", 0), 0),   
                round(reaction.get("U3", 0), 0)     
            ])
        return vkt.TableResult(
            data, 
            row_headers=["Sup 1","Sup 2","Sup 3","Sup 4"],
            column_headers=["Node", "Load Case","U1[N]", "U2[N]", "U3[N]"],
        )