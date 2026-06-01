# CadQuery Patterns

These patterns are distilled from the local modeling workspace.

## Axis Cylinders

```python
def cylinder_x(start_x, length, radius, center_y=0.0, center_z=0.0):
    return (
        cq.Workplane("YZ")
        .workplane(offset=start_x)
        .center(center_y, center_z)
        .circle(radius)
        .extrude(length)
    )

def cylinder_z(start_z, length, radius, center_x=0.0, center_y=0.0):
    return (
        cq.Workplane("XY")
        .workplane(offset=start_z)
        .center(center_x, center_y)
        .circle(radius)
        .extrude(length)
    )
```

## Frustum Cutter

```python
def frustum_z(start_z, length, bottom_radius, top_radius, center_x=0.0, center_y=0.0):
    return (
        cq.Workplane("XY")
        .workplane(offset=start_z)
        .center(center_x, center_y)
        .circle(bottom_radius)
        .workplane(offset=length)
        .circle(top_radius)
        .loft(combine=True)
    )
```

## Hollow Tube

```python
tube = cylinder_z(0.0, tube_length, outer_radius)
bore = cylinder_z(-0.2, tube_length + 0.4, inner_radius)
tube = tube.cut(bore).edges("%Circle").chamfer(end_chamfer).clean()
```

## External Thread

Use for functional-looking small connectors:

```python
helix = cq.Wire.makeHelix(pitch, thread_length, mid_radius, center=(0, 0, z0), dir=(0, 0, 1))
profile = cq.Workplane("XZ").center(mid_radius, z0).ellipse(radial_radius, profile_width / 2)
ridge = profile.sweep(helix, isFrenet=True, transition="round").clean()
part = part.union(ridge).clean()
```

## Internal Female Thread Ridge

For a socket where the thread protrudes inward:

```python
helix = cq.Wire.makeHelix(pitch, height, thread_mid_radius, center=(cx, cy, z0), dir=(0, 0, 1))
profile = cq.Workplane("XZ").center(cx + thread_mid_radius, z0).ellipse(thread_radial_radius, profile_width / 2)
thread_crest = profile.sweep(helix, isFrenet=True, transition="round").clean()
socket = socket_body.cut(clearance).union(thread_crest).cut(through_bore).clean()
```

## Cutaway

Build the sectioned body before adding fragile helical details when possible:

```python
cut_box = cq.Workplane("XY").box(w, d, h, centered=(False, False, False)).translate((x, y, z))
sectioned = make_body().cut(cut_box)
sectioned = cut_channels_and_sockets(sectioned)
sectioned = sectioned.union(make_thread().cut(cut_box)).clean()
```

## Assembly Fit Check

```python
assembly = cq.Assembly(name="fit_check")
assembly.add(base_model, name="base")
assembly.add(mating_model.translate((dx, dy, dz)), name="mating_part")
assembly.save(str(output_step))
```
