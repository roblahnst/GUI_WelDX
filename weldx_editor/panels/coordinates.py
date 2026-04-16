import numpy as np
import streamlit as st
from weldx_editor.utils.style import COLORS


def render_coordinates(state):
    """
    Render the coordinates panel with two tabs:
    - KOS-Hierarchie: Coordinate system tree hierarchy
    - Transformationen: Transformation matrix editor
    """

    # Initialize coordinate systems if not present
    if not hasattr(state, 'coordinate_systems'):
        state.coordinate_systems = {}

    # Initialize default systems if empty
    if not state.coordinate_systems:
        state.coordinate_systems = {
            'robot_base': {'name': 'robot_base', 'status': 'complete', 'parent': None},
            'tcp': {'name': 'tcp', 'status': 'complete', 'parent': 'robot_base'},
        }

    tab1, tab2 = st.tabs(["KOS-Hierarchie", "Transformationen"])

    # ========== TAB 1: KOS-Hierarchie ==========
    with tab1:
        st.subheader("Koordinatensystem-Hierarchie")

        # Build and display tree
        st.write("**Verfügbare Koordinatensysteme:**")

        tree_text = _build_kos_tree(state.coordinate_systems)
        st.code(tree_text, language="text")

        st.divider()

        # Add new coordinate system
        st.subheader("Neues Koordinatensystem hinzufügen")
        with st.expander("➕ Koordinatensystem hinzufügen"):
            with st.form("add_kos_form", border=False):
                kos_name = st.text_input(
                    "Name des Koordinatensystems",
                    key="new_kos_name"
                )

                # Get list of existing systems for parent selection
                existing_systems = list(state.coordinate_systems.keys())
                parent_system = st.selectbox(
                    "Übergeordnetes System",
                    options=existing_systems,
                    key="kos_parent"
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    trans_x = st.number_input(
                        "Translation X (mm)",
                        value=0.0,
                        key="kos_trans_x"
                    )
                with col2:
                    trans_y = st.number_input(
                        "Translation Y (mm)",
                        value=0.0,
                        key="kos_trans_y"
                    )
                with col3:
                    trans_z = st.number_input(
                        "Translation Z (mm)",
                        value=0.0,
                        key="kos_trans_z"
                    )

                st.write("**Rotation (optional):**")
                rot_type = st.radio(
                    "Rotationsformat",
                    options=["Euler Winkel (deg)", "Quaternion", "Keine"],
                    horizontal=True,
                    key="kos_rot_type"
                )

                if rot_type == "Euler Winkel (deg)":
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        rot_x = st.number_input("Roll (°)", value=0.0, key="kos_roll")
                    with col2:
                        rot_y = st.number_input("Pitch (°)", value=0.0, key="kos_pitch")
                    with col3:
                        rot_z = st.number_input("Yaw (°)", value=0.0, key="kos_yaw")
                    rotation = {'type': 'euler', 'x': rot_x, 'y': rot_y, 'z': rot_z}
                elif rot_type == "Quaternion":
                    col1, col2 = st.columns(2)
                    with col1:
                        col_q1, col_q2 = st.columns(2)
                        with col_q1:
                            qw = st.number_input("w", value=1.0, key="kos_qw")
                        with col_q2:
                            qx = st.number_input("x", value=0.0, key="kos_qx")
                    with col2:
                        col_q3, col_q4 = st.columns(2)
                        with col_q3:
                            qy = st.number_input("y", value=0.0, key="kos_qy")
                        with col_q4:
                            qz = st.number_input("z", value=0.0, key="kos_qz")
                    rotation = {'type': 'quaternion', 'w': qw, 'x': qx, 'y': qy, 'z': qz}
                else:
                    rotation = None

                if st.form_submit_button("Koordinatensystem speichern"):
                    if kos_name and kos_name not in state.coordinate_systems:
                        state.coordinate_systems[kos_name] = {
                            'name': kos_name,
                            'status': 'incomplete',
                            'parent': parent_system,
                            'translation': {'x': trans_x, 'y': trans_y, 'z': trans_z},
                            'rotation': rotation
                        }
                        st.success(f"Koordinatensystem '{kos_name}' hinzugefügt!")
                    elif kos_name in state.coordinate_systems:
                        st.error(f"Koordinatensystem '{kos_name}' existiert bereits.")
                    else:
                        st.error("Bitte geben Sie einen Namen ein.")

    # ========== TAB 2: Transformationen ==========
    with tab2:
        st.subheader("Transformationen zwischen Koordinatensystemen")

        st.write("**Transformationsmatrizen:**")

        if not state.coordinate_systems:
            st.info("Noch keine Koordinatensysteme vorhanden.")
        else:
            # Display transformation matrix for each system with parent
            for kos_name, kos_info in state.coordinate_systems.items():
                if kos_info.get('parent'):
                    parent = kos_info['parent']
                    st.write(f"**{parent} → {kos_name}**")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**Translation (mm):**")
                        trans = kos_info.get('translation', {'x': 0, 'y': 0, 'z': 0})
                        trans_x = st.number_input(
                            "X",
                            value=trans.get('x', 0.0),
                            key=f"trans_x_{kos_name}"
                        )
                        trans_y = st.number_input(
                            "Y",
                            value=trans.get('y', 0.0),
                            key=f"trans_y_{kos_name}"
                        )
                        trans_z = st.number_input(
                            "Z",
                            value=trans.get('z', 0.0),
                            key=f"trans_z_{kos_name}"
                        )

                        # Update state
                        kos_info['translation'] = {'x': trans_x, 'y': trans_y, 'z': trans_z}

                    with col2:
                        st.write("**Rotation:**")
                        rotation = kos_info.get('rotation')
                        if rotation and rotation.get('type') == 'euler':
                            rot_x = st.number_input(
                                "Roll (°)",
                                value=rotation.get('x', 0.0),
                                key=f"rot_x_{kos_name}"
                            )
                            rot_y = st.number_input(
                                "Pitch (°)",
                                value=rotation.get('y', 0.0),
                                key=f"rot_y_{kos_name}"
                            )
                            rot_z = st.number_input(
                                "Yaw (°)",
                                value=rotation.get('z', 0.0),
                                key=f"rot_z_{kos_name}"
                            )
                            kos_info['rotation'] = {'type': 'euler', 'x': rot_x, 'y': rot_y, 'z': rot_z}
                        elif rotation and rotation.get('type') == 'quaternion':
                            qw = st.number_input(
                                "w",
                                value=rotation.get('w', 1.0),
                                key=f"qw_{kos_name}"
                            )
                            qx = st.number_input(
                                "x",
                                value=rotation.get('x', 0.0),
                                key=f"qx_{kos_name}"
                            )
                            qy = st.number_input(
                                "y",
                                value=rotation.get('y', 0.0),
                                key=f"qy_{kos_name}"
                            )
                            qz = st.number_input(
                                "z",
                                value=rotation.get('z', 0.0),
                                key=f"qz_{kos_name}"
                            )
                            kos_info['rotation'] = {
                                'type': 'quaternion',
                                'w': qw,
                                'x': qx,
                                'y': qy,
                                'z': qz
                            }
                        else:
                            st.caption("Keine Rotation definiert")

                    # Transformation matrix visualization
                    with st.expander(f"Transformationsmatrix (4x4)"):
                        trans_data = kos_info.get('translation', {'x': 0, 'y': 0, 'z': 0})
                        rot_data = kos_info.get('rotation')

                        # Build a simple transformation matrix representation
                        matrix_text = "┌                          ┐\n"
                        matrix_text += "│  1.00   0.00   0.00  {: >6.2f} │\n".format(trans_data.get('x', 0))
                        matrix_text += "│  0.00   1.00   0.00  {: >6.2f} │\n".format(trans_data.get('y', 0))
                        matrix_text += "│  0.00   0.00   1.00  {: >6.2f} │\n".format(trans_data.get('z', 0))
                        matrix_text += "│  0.00   0.00   0.00   1.00  │\n"
                        matrix_text += "└                          ┘\n"

                        st.code(matrix_text, language="text")

                        if rot_data:
                            if rot_data.get('type') == 'euler':
                                st.caption(
                                    f"Euler angles: "
                                    f"Roll={rot_data.get('x', 0):.1f}°, "
                                    f"Pitch={rot_data.get('y', 0):.1f}°, "
                                    f"Yaw={rot_data.get('z', 0):.1f}°"
                                )
                            elif rot_data.get('type') == 'quaternion':
                                st.caption(
                                    f"Quaternion: "
                                    f"w={rot_data.get('w', 1):.3f}, "
                                    f"x={rot_data.get('x', 0):.3f}, "
                                    f"y={rot_data.get('y', 0):.3f}, "
                                    f"z={rot_data.get('z', 0):.3f}"
                                )

                    st.divider()

        st.divider()
        _render_3d_visualization(state)


# ─── 3D Visualization ─────────────────────────────────────────

# ─── 3D Visualization (PyVista / VTK) ─────────────────────────

def _render_3d_visualization(state):
    """Render interactive 3D visualization using Three.js with direct geometry."""
    import json

    cs = state.coordinate_systems
    meshes = getattr(state, "workpiece_meshes", [])

    if not cs and not meshes:
        st.info("Keine Koordinatensysteme vorhanden.")
        return

    has_data = meshes or any(
        isinstance(info.get("translation"), dict) for info in cs.values()
    )
    if not has_data:
        st.info("Keine Transformationsdaten vorhanden.")
        return

    st.subheader("3D-Visualisierung")

    # ── Prepare mesh data (clean NaN + decimate) ──
    mesh_json = []
    for mesh_data in meshes:
        verts = mesh_data["vertices"].astype(np.float64)
        tris = mesh_data["triangles"].astype(np.int64)

        # Remove NaN vertices
        nan_mask = np.isnan(verts).any(axis=1)
        if nan_mask.any():
            valid_tri = ~(nan_mask[tris[:, 0]] | nan_mask[tris[:, 1]] | nan_mask[tris[:, 2]])
            tris = tris[valid_tri]
            used = np.unique(tris)
            remap = np.full(verts.shape[0], -1, dtype=np.int64)
            remap[used] = np.arange(len(used))
            verts = verts[used]
            tris = remap[tris]

        # Decimate with PyVista/VTK if available
        if tris.shape[0] > 80_000:
            try:
                import pyvista as pv
                import vtk
                vtk.vtkLogger.SetStderrVerbosity(vtk.vtkLogger.VERBOSITY_OFF)
                faces = np.column_stack([np.full(tris.shape[0], 3, dtype=np.int64), tris]).ravel()
                pv_mesh = pv.PolyData(verts, faces)
                alg = vtk.vtkQuadricClustering()
                alg.SetInputData(pv_mesh)
                alg.SetNumberOfXDivisions(300)
                alg.SetNumberOfYDivisions(300)
                alg.SetNumberOfZDivisions(300)
                alg.Update()
                dec = pv.wrap(alg.GetOutput())
                verts = np.asarray(dec.points)
                tris = dec.faces.reshape(-1, 4)[:, 1:4]
            except ImportError:
                # Fallback: stride sampling
                step = max(1, tris.shape[0] // 80_000)
                tris = tris[::step]
                used = np.unique(tris)
                remap2 = np.full(verts.shape[0], -1, dtype=np.int64)
                remap2[used] = np.arange(len(used))
                verts = verts[used]
                tris = remap2[tris]

        mesh_json.append({
            "v": verts.ravel().tolist(),
            "i": tris.ravel().tolist(),
        })

    # ── Prepare trajectory data ──
    traj_json = []
    for name, info in cs.items():
        traj = info.get("trajectory")
        if traj is None or not hasattr(traj, "shape") or traj.shape[0] < 2:
            continue
        if not any(k in name.lower() for k in ("tcp", "tool", "trace", "design")):
            continue
        pts = traj[::max(1, traj.shape[0] // 500)].astype(np.float64)
        traj_json.append({"name": name, "pts": pts.ravel().tolist()})

    # ── Prepare label data ──
    label_json = []
    for name, info in cs.items():
        t = info.get("translation")
        if not isinstance(t, dict):
            continue
        color = "#cc0000" if any(k in name.lower() for k in ("tcp", "design")) \
            else "#00aa00" if any(k in name.lower() for k in ("t1", "t2")) \
            else "#333333"
        label_json.append({"name": name, "pos": [t["x"], t["y"], t["z"]], "color": color})

    # ── Build HTML ──
    scene_data = json.dumps({"meshes": mesh_json, "trajectories": traj_json, "labels": label_json})
    html = _THREEJS_VIEWER_HEAD + scene_data + _THREEJS_VIEWER_TAIL
    st.components.v1.html(html, height=650, scrolling=False)


_THREEJS_VIEWER_HEAD = """<!DOCTYPE html>
<html><head><style>
  html, body { margin:0; padding:0; width:100%; height:100%; overflow:hidden;
               background:#f8fafc; font-family:Arial,sans-serif; }
  canvas { display:block; }
</style></head><body>
<script id="sceneData" type="application/json">
"""

_THREEJS_VIEWER_TAIL = """
</script>
<script type="importmap">
{ "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
} }
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const DATA = JSON.parse(document.getElementById('sceneData').textContent);

// Scene
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf8fafc);

// Lighting
scene.add(new THREE.AmbientLight(0xffffff, 0.5));
const dir1 = new THREE.DirectionalLight(0xffffff, 0.7);
dir1.position.set(200, 300, 400);
scene.add(dir1);
const dir2 = new THREE.DirectionalLight(0xffffff, 0.3);
dir2.position.set(-200, -100, -300);
scene.add(dir2);

// Camera + Renderer
const camera = new THREE.PerspectiveCamera(45, window.innerWidth/window.innerHeight, 0.1, 100000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.rotateSpeed = 0.8;
controls.zoomSpeed = 1.2;
controls.panSpeed = 0.8;
controls.screenSpacePanning = true;

// Bounding box for auto-fit
const sceneBox = new THREE.Box3();

// ── Add workpiece meshes ──
const meshMaterial = new THREE.MeshPhongMaterial({
  color: 0x808080, side: THREE.DoubleSide,
  shininess: 30, flatShading: false,
});

DATA.meshes.forEach(m => {
  const geom = new THREE.BufferGeometry();
  geom.setAttribute('position', new THREE.Float32BufferAttribute(m.v, 3));
  geom.setIndex(m.i);
  geom.computeVertexNormals();
  const mesh = new THREE.Mesh(geom, meshMaterial);
  scene.add(mesh);
  sceneBox.expandByObject(mesh);
});

// ── Add trajectories ──
DATA.trajectories.forEach(t => {
  const pts = [];
  for (let i = 0; i < t.pts.length; i += 3) {
    pts.push(new THREE.Vector3(t.pts[i], t.pts[i+1], t.pts[i+2]));
  }
  const geom = new THREE.BufferGeometry().setFromPoints(pts);
  const mat = new THREE.LineBasicMaterial({ color: 0xcc0000, linewidth: 2 });
  scene.add(new THREE.Line(geom, mat));
});

// ── Add labels ──
function makeLabel(text, pos, color) {
  const canvas = document.createElement('canvas');
  canvas.width = 256; canvas.height = 64;
  const ctx = canvas.getContext('2d');
  ctx.font = 'bold 24px Arial';
  ctx.fillStyle = color;
  ctx.textAlign = 'center';
  ctx.fillText(text, 128, 40);
  const tex = new THREE.CanvasTexture(canvas);
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(mat);
  sprite.position.set(pos[0], pos[1], pos[2]);
  const s = sceneBox.getSize(new THREE.Vector3()).length() * 0.06;
  sprite.scale.set(s * 2, s * 0.5, 1);
  return sprite;
}
DATA.labels.forEach(l => scene.add(makeLabel(l.name, l.pos, l.color)));

// ── Fit camera ──
const center = sceneBox.getCenter(new THREE.Vector3());
const size = sceneBox.getSize(new THREE.Vector3()).length();
camera.position.copy(center).add(new THREE.Vector3(size*0.5, size*0.35, size*0.7));
camera.near = size * 0.001;
camera.far = size * 10;
camera.updateProjectionMatrix();
controls.target.copy(center);
controls.update();

// Grid
const grid = new THREE.GridHelper(size * 1.5, 20, 0xcccccc, 0xe8e8e8);
grid.position.copy(center);
grid.position.y = sceneBox.min.y - 0.01;
scene.add(grid);

// ── Axes ──
function axisLine(from, to, color) {
  const g = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(...from), new THREE.Vector3(...to)
  ]);
  return new THREE.Line(g, new THREE.LineBasicMaterial({ color }));
}
const ax = size * 0.12;
const o = [sceneBox.min.x, sceneBox.min.y, sceneBox.max.z];
scene.add(axisLine(o, [o[0]+ax, o[1], o[2]], 0xe74c3c));
scene.add(axisLine(o, [o[0], o[1]+ax, o[2]], 0x2ecc71));
scene.add(axisLine(o, [o[0], o[1], o[2]-ax], 0x3498db));
scene.add(makeLabel('X', [o[0]+ax*1.3, o[1], o[2]], '#e74c3c'));
scene.add(makeLabel('Y', [o[0], o[1]+ax*1.3, o[2]], '#2ecc71'));
scene.add(makeLabel('Z', [o[0], o[1], o[2]-ax*1.3], '#3498db'));

// Render loop
(function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
})();

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
</script></body></html>"""


def _build_kos_tree(coordinate_systems: dict, parent=None, indent=0) -> str:
    """
    Build a tree representation of coordinate system hierarchy.

    Args:
        coordinate_systems: Dictionary of coordinate system info
        parent: Parent system name to filter by
        indent: Current indentation level

    Returns:
        String representation of the tree
    """
    tree_lines = []

    # Find root systems on first call
    if parent is None:
        root_systems = [
            name for name, info in coordinate_systems.items()
            if info.get('parent') is None
        ]
        for root in root_systems:
            tree_lines.append(_format_kos_line(coordinate_systems[root], 0))
            tree_lines.extend(_build_kos_subtree(coordinate_systems, root, 0))
        return '\n'.join(tree_lines) if tree_lines else "Keine Koordinatensysteme vorhanden"
    else:
        return _build_kos_subtree(coordinate_systems, parent, indent)


def _build_kos_subtree(coordinate_systems: dict, parent: str, indent: int) -> list:
    """
    Recursively build subtree for a parent coordinate system.

    Args:
        coordinate_systems: Dictionary of coordinate system info
        parent: Parent system name
        indent: Current indentation level

    Returns:
        List of tree lines
    """
    lines = []
    children = [
        name for name, info in coordinate_systems.items()
        if info.get('parent') == parent
    ]

    for i, child in enumerate(children):
        is_last = (i == len(children) - 1)
        prefix = "└── " if is_last else "├── "
        lines.append(prefix + _format_kos_line(coordinate_systems[child], indent + 1))

        # Recursively add children
        child_lines = _build_kos_subtree(coordinate_systems, child, indent + 2)
        for j, line in enumerate(child_lines):
            if is_last:
                lines.append("    " + line)
            else:
                lines.append("│   " + line)

    return lines


def _format_kos_line(kos_info: dict, indent: int) -> str:
    """
    Format a single coordinate system line with status indicator.

    Args:
        kos_info: Coordinate system information dictionary
        indent: Indentation level

    Returns:
        Formatted string for the coordinate system
    """
    name = kos_info.get('name', 'unknown')
    status = kos_info.get('status', 'unknown')

    if status == 'complete':
        icon = "✅"
    elif status == 'incomplete':
        icon = "❌ (fehlt)"
    else:
        icon = "⚠️"

    return f"{name} {icon}"
