# Notes

[Blender 4.2 - Extensions Replace Addons](https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html#extensions-getting-started)

## Setup

To make switching between branches easier, I've added a symlink to the `sparrow` addon in the Blender config directory. This way, I can just switch branches and the addon will always be up to date.

Could so set additional script directory to blender

```bash
cd ~/.config/blender/4.3/scripts/addons 
ln -s ~/code/p/sparrow/addons/sparrow/ sparrow
```
