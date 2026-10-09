# SMIRK - Freeform Facial Features
---
https://github.com/user-attachments/assets/10f9663b-4e68-4994-bae1-f1d43b5a1ef8
## What is SMIRK?

SMIRK is a system designed to help with stylized facial features like mouths and openings in general. 
It can be used for eyes and more as well.

At it's core it's a set of tools that allows the user to cut a hole into the mesh using a circular base.
This can be an edge loop on a mouth mesh, a simple mesh ribbon or even Grease Pencil

Many might know this as the *"Boolean Mouth"* but **SMIRK** comes with a subset of methods to approach the cutting process to enable maximum flexibility and performance in a production environment.
## Installation

You can install directly within Blender, by searching for SMIRK inside the "Get Extensions" panel.

You can also manually install it by going to the Releases panel here on the right and downloading the newest Zip File. This can be drag and dropped into Blender to be installed.
## What it isn't

- SMIRK is not an auto-rigger and does not generate any armatures to make facial features animatable. This might change in the future when the scope of this addon changes.
- SMIRK does not generate entire facial features. It does come with some mesh generation like the Rim and Inner Area which might be expanded on in the future.
- SMIRK cannot be exported to game engines as it makes use of Blender's shaders and Geometry Nodes. Though a similar approach could possibly be recreated in a game engine.
## Getting Started

<details>
  <summary>Quick Setup</summary>
  
- Setup your objects first. You'll need a surface object like a head and a cutter object like Grease Pencil object or a Mouth Mesh/Circular Mesh. 
- Open your Side Panel and select the **SMIRK** Panel.
- Select your Surface Mesh and click on **Setup Proxy** to create a **Proxy Mesh** (used internally to avoid dependency cycles)
- Click on **Add Smirk Modifier** and fill in the fields, choose your cutter object as the cutter
- Go to the new **Cutter Object** Subpanel
- Now depending on the type of Cutter (Object or Grease Pencil) you click on **Add SMIRK Cutter Vertex Group/GP Layer**
- **Click on Edit Cutter Object** to edit the cutter (you can do this manually too of course but this operator does some helpful additional things)
- For Vertex Groups, select an edge loop and add it to your **Cutter Mask Vertex Group**
- For Grease Pencil, edit on the **Cutter Mask Layer** and either use the fill tool to create the cutter or draw them manually (Make sure to make the drawn strokes cyclic in edit mode)
- Click **Go to Surface Object** to return to the Surface
- The basic setup is done and the modifier can now be further tweaked
</details>

## Wasn't This Released Before?

The SMIRK addon is an extension to the Geometry Nodes toolset I made a year ago with the same name. 

This addon wraps these Geometry Node tools into a Blender extension that helps set up and adjust the Freeform Facial Feature workflow easily.
## Documentation

More thorough documentation will follow soon, for now you can learn about the general concepts using some older videos I have made here:

[Detached Facial Features in Blender](https://www.youtube.com/watch?v=RLNl8FHurM0)

[SMIRK Freeform Facial Features](https://www.youtube.com/watch?v=RLNl8FHurM0)

[Old Notion page describing the manual setup of the original asset](https://app.notion.com/p/chrysalis-project/Initial-Setup-1eda5f597cfe801594acf81f1f2d8a87?source=copy_link)







