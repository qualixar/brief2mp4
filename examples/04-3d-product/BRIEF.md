# Brief 04: 3D pack, "Everything inside."

Make an 8-second 3D product shot with the optional 3D pack: the parts of a small gadget drop in and settle into a stack, the stack opens into an exploded view, and a title closes the shot. It needs the pack's `core` component (see `plugin/skills/brief2mp4/3d/README-3D.md`); no Blender and no CAD component.

- Delivery: final.mp4, 1920x1080, 30 fps, exactly 8.0 s, H.264 + AAC.
- The product: an original, generic pocket-sized sensor, no brand and no logo. Five parts, stacked from the bottom: a dark matte tray (60 x 40 x 10 mm, rounded corners, a shallow pocket in the top), a brushed-aluminium battery slab, a dark green circuit board with three small chips, a white ceramic-look cover, and a small smoked-glass lens disc on top.
- Set: a dark neutral grey gradient background with a soft contact shadow under the parts. No visible floor edge, no horizon line.
- Motion, 0.0 to 3.0 s: the parts fall one after another from above the frame, bottom part first, each landing on the one below with a small wobble, and settle into a neat stack. Real rigid-body physics, not hand-keyed.
- Camera: starts wide and above, pushes in on the settled stack by 3.0 s, then pulls back to frame the whole exploded column by 5.0 s and drifts slightly closer until the end.
- Exploded view, 3.2 to 4.6 s: the parts rise apart along the vertical axis with an ease in and out, the bottom tray staying put, each part higher than the one below. Hold the exploded view to the end.
- At 5.3 s the title "Everything inside." appears bottom left with the line "Five parts, one pocket-sized sensor." under it, and fades out before the end. No kicker line above it.
- Look: neutral tone mapping, a dim environment and a strong key light, bloom off, nothing glowing.
- Sound: a quiet soundtrack with a soft low thud for each landing and a light rising sweep for the exploded view.
- Check before the full render: snapshot at 1.2 s, 2.9 s, 3.9 s and 7.8 s and look at the frames.

The worked build for this brief ships with the pack: `plugin/skills/brief2mp4/3d/examples/04-3d-product/` holds the spec (`device.py`), the physics scene, the shot JSON and `build.py`, which runs every step.
