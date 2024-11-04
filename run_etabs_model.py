import comtypes.client
import pythoncom
import json
from pathlib import Path

def create_etabs_model():
    # Initialize ETABS model
    program_path=r"C:\Program Files\Computers and Structures\ETABS 22\ETABS.exe"
    pythoncom.CoInitialize()
    try:
        helper = comtypes.client.CreateObject("ETABSv1.Helper")
        helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)
        EtabsEngine = helper.CreateObject(program_path)
        EtabsEngine.ApplicationStart()
        EtabsObject = EtabsEngine.SapModel
        EtabsObject.InitializeNewModel(9)  # Set units to mm
        EtabsObject.File.NewBlank()
    finally:
        pythoncom.CoUninitialize()
    # Create joints
    input_json = Path.cwd() / "inputs.json"
    with open(input_json) as jsonfile:
        data = json.load(jsonfile)
    nodes, lines = data[:]

    # Create nodes
    for id, node in nodes.items():
        ret, _ = EtabsObject.PointObj.AddCartesian(
            node["x"], node["y"], node["z"], " ", str(id)
        )

    # Create members
    MATERIAL_CONCRETE = 2
    ret = EtabsObject.PropMaterial.SetMaterial("CONC", MATERIAL_CONCRETE)
    ret = EtabsObject.PropMaterial.SetMPIsotropic("CONC", 30000, 0.2, 0.0000055)
    section_name = "300x300 RC"
    ret = EtabsObject.PropFrame.SetRectangle(section_name, "CONC", 300, 300)
    for id, line in lines.items():
        point_i = line["node_i"]
        point_j = line["node_j"]
        ret, _ = EtabsObject.FrameObj.AddByPoint(
            str(point_i), str(point_j), str(id), section_name, "Global"
        )

    # Add rigid supports
    list_nodes = [1, 2, 5, 6]
    for node_id in list_nodes:
        ret = EtabsObject.PointObj.SetRestraint(str(node_id), [1, 1, 1, 1, 1, 1])

    EtabsObject.View.RefreshView(0, False)
    # Create the model and run the analysis
    file_path = Path.cwd() / "etabsmodel.edb"
    EtabsObject.File.Save(str(file_path))
    EtabsObject.Analyze.RunAnalysis()

    # Get the reaction loads
    load_case = "Dead"
    ret = EtabsObject.Results.Setup.DeselectAllCasesAndCombosForOutput()
    reactions_list = list()
    ret = EtabsObject.Results.Setup.SetCaseSelectedForOutput(load_case)
    for node in list_nodes:
        *_, U1, U2, U3, R1, R2, R3, ret = EtabsObject.Results.JointReact(
            str(node), 0, 0
        )
        reaction = {
            "Node": str(node),
            "LoadCase": load_case,
            "U1": U1[0],
            "U2": U2[0],
            "U3": U3[0],
            "R1": R1[0],
            "R2": R2[0],
            "R3": R3[0],
        }
        reactions_list.append(reaction)
        
    # Save the output in a JSON
    output = Path.cwd() / "output.json"
    with open(output, "w") as jsonfile:
        json.dump(reactions_list, jsonfile)

    ret = EtabsEngine.ApplicationExit(False)

    return ret

if __name__ == "__main__":
    create_etabs_model()