# SMIRK Modifier

## Inputs

##### Mode
: Choose between two modes which toggle specific features
: 
 **Simple**
: Simple is a simplified Version of the tool that works great with a mesh-based approach

: 
**Complex**
: Complex adds Cutter Rim and Inner Area and is best suited for a Grease Pencil approach

##### Exclude Area
##### Exclusion Mask
: The parts of the geometry that go into the first output
### :fontawesome-solid-scissors: Cutter
---
##### Mask
: Name of the Vertex Group or GP Layer used to determine the Body opening
##### UV Map
: UV Map to transfer from. Important to fix UVs that might get broken through certain options
##### Object
: Object that drives the Smirk Boolean
##### Collection
: Collection that drives the Smirk Boolean
##### Separate Instances
: Instead of displaying all objects of the collection, only display one
##### Object Index
: determines which Instance to display. Reads the collection top down
#### Extractor
##### Mode
: Algorithm used to create the Cutter Mask
##### Grid Resolution
: Resolution of the Grid. Higher gives more accurate results
##### Offset
: Offsets the Grid Fill, basically spinning it around. Might help with quality in some cases
##### Blur Iterations
##### Quality
: Subdivides the Cutter Mesh before Shrinkwrapping it
##### Projected Shrinkwrap
: Uses Projected Shrinkwrap in addition to Nearest Surface which should yield better results, especially around harsher angles
##### Hardsurface Precision
: Uses Manifold Boolean to calculate a better mask for Sharp Edges. Both this and the Cutter Mesh need to be manifold. Optimal for Hardsurface Objects. Has a performance impact
### Shader Mask
---
##### Threshold
#### Output Attributes
##### Shader Attribute
: Attribute for the Mask used in the Shader to control Transparency
#### Blur Attribute
##### Iterations
##### Weight
### Manifold Boolean
---
##### Cutter Width
##### Resample
: Resample the curve that drives the Boolean Cutter topology to control the resolution
##### Resolution
: The resolution of the Boolean Cutter. When turned off it uses the resolution of the Cutter Object
### Adaptive Subdivision
---
##### Iterations
: How often the mesh gets subdivided. Higher values increase accuratcy but also performance
##### Radius
: Overall Radius where Tesselation happens
##### Threshold
: Determines thickness where each subdivision iteration takes places
##### Subdivide entire Cutter
: Subdivides the entire Cutter Area instead of just around the boundary. Can lead to more accurate results with Cutout Mesh at the cost of performance
### Cutout Mesh
---
##### Threshold
: Determines when faces should be deleted. Higher values create a larger hole
##### Mode
: Algorithm used to snap the created boundary edge to back the Cutter
##### Snap to Cutter
: Snaps the Boundary Edge to the cutter
##### Smooth Snapping
: Smooths the area around the snapped Boundary Edge to create a cleaner mesh
##### Smooth Iterations
: Intensity of the smoothing. High Values slow down performance
##### Turn off Shader Mask
: Turns the Shader Mask fully opaque to not interfere with the Cutout Mesh. 
### Cutter Rim
---
#### Adjust
##### Projected Shrinkwrap
##### Material
: Material should be identical to the head but using the Custom Normal attribute to drive the Normal
##### Rim Type
: Algorithm used to create the Rim
##### Loop Cuts
: Add Loop Cuts to the Rim
##### Thickness
: Overall Thickness of the Rim
##### Width
: Width of the Rim
##### Height
: Height of the Rim
##### Reduce Overlap
: Reduces mesh overlap around sharp corners but potentially creates uneven thickness
##### Smooth Loft
: Blur the generated Lofting Curve to get a smoother result
##### Shrinkwrap Offset
: Adjust how closely the Rim snaps to the Object
##### Resample
: Resample the curve that drives the Cutter Rim topology to control the resolution
##### Resolution
: The resolution of the Rim opening. When turned off it uses the resolution of the Cutter Object
#### Legacy
##### Flip
: Flips the direction of the Rim. New dynamic algorithm should hopefully make this option obsolete
##### Flip Vertex Group
: Vertex Group used to manually flip Curves. Use this to fix some inconsistencies. Can also flip manual Loft Curves
#####  Custom Normal Attribute
: Attribute you use to adjust the normals of the Mouth Rim Material. 4.5 allows normals to be transferred directly so this shouldn't be needed anymore
### Inner Area
---
#### Adjust
##### Scale Inner Area
: Scale the opening of the Inner Area
##### Offset
: Moves the Inner Area towards the inside of the mesh
##### Smooth Opening
: Smooths the start of the Inner Area. Useful for very angular mouths and to reduce overlap
##### Smooth Amount
: Mix between unsmoothed and smoothed curve
##### Loop Cuts
: Add Loop Cuts to the Inner Area
##### Extrude Depth
: Determines how far the Inner Area reaches into the object
##### Backside Type
: Algorithm used to create the Backside of the Inner Area
##### Grid Offset
: Rotates the generated Grid Backside
##### Merge Backside
: Merges the Backside to a single point
##### Triangulate Backside
: Triangulates the Backside. Might give decent results with the N-Gon Type
##### Scale Backside
: Scales the Backside
##### Flatten Backside
: Amount of mixing between the A and B inputs
##### Smooth Amount
: Controls the smoothness of the Inner Area
##### Expand Area
: Exapnds the Inner Area when smoothed
##### Rotate Inner Area
: Rotate the angle at which the Inner Area gets extruded
##### Match To Cutout
##### Simplify Curve
: Dissolves Points using an angle threshold. Allows for lower mesh density that still matches the cutout
#### Shading
##### Material
: Material of the Inner Area
##### Shade Smooth
: Shade the Inner Area smooth
##### Blur Normals
: Blur the normals of the Inner Area
##### Resample
: Resample the curve that drives the Inner Area topology to control the resolution
##### Resolution
: The resolution of the Inner Area opening. When turned off it uses the resolution of the Cutter Object

## Outputs


## :material-eye: Viewport Settings
