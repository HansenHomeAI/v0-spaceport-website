# Mapbox Editor Manual Test Plan

## 1. Unit/Logic-Level Checks (Implicitly tested during drag)
- [ ] **Curved Path Generation**: Drag a waypoint to form a sharp turn. The path drawn should form a smooth circular arc on the inside of the angle, not a straight pointed line.
- [ ] **Undo/Redo Stack**:
  - Drag waypoint A, then drag waypoint B.
  - Click `Undo` twice. It should restore waypoint B, then waypoint A to their original positions.
  - Click `Redo` twice. It should re-apply the drags.
  - After a new drag, Redo stack should be cleared (Redo button becomes disabled).

## 2. In-App Behavior
- [ ] **Basic Editing Flow**:
  - Open `NewProjectModal`, pick center, optimize, toggle battery 1.
  - Enter Fullscreen mode.
  - Check "Edit Path" to enable editing.
  - Drag a marker (white circle with blue border). The path should redraw smoothly while dragging.
  - Release the drag. Toggle fullscreen off and on; the edited position must persist.
- [ ] **AGL Recompute**:
  - Note the general altitude layout of the path.
  - Drag a waypoint over a hill or structure (if visible in Mapbox 3D terrain/satellite) or far away.
  - Click `Refresh Altitude`.
  - Expect a success notification indicating altitudes have been adjusted based on terrain differences.
- [ ] **Safety & Scoping**:
  - Outside of fullscreen, editing is not possible (no markers visible).
  - Toggling "Edit Path" hides markers.
  - Edits on Battery 1 do not affect Battery 2.

## 3. CSV Export Validation
- [ ] **Export Integrity**:
  - Make an edit on Battery 1.
  - Click `Download CSV` for Battery 1.
  - Open the CSV and verify the changed `latitude` and `longitude` fields match the drag displacement, and `altitude(ft)` is updated if `Refresh Altitude` was clicked.

## 4. UX & Mobile Quality
- [ ] **Hit Areas**: On a touch screen or mobile emulator, the markers should be easy to grab.
- [ ] **UI Placement**: The Edit Path toggle, Undo, and Redo buttons should be comfortably reachable and not block Mapbox controls.
- [ ] **Panning/Zooming**: Dragging the map background still pans normally. Dragging a marker only moves the marker.