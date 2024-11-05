import bpy

# Get the selected object
selected_obj = bpy.context.object

# Ensure an object is selected
if selected_obj is None:
    raise Exception("Please select an object with children")

# Loop through the children of the selected object
for child in selected_obj.children:
    child_name = child.name
    
    # Check if a collection with the same name already exists
    if child_name in bpy.data.collections:
        collection = bpy.data.collections[child_name]
    else:
        # Create a new collection for the child
        collection = bpy.data.collections.new(child_name)
        bpy.context.scene.collection.children.link(collection)
    
    # Create a collection instance at the child's original location
    original_location = child.location.copy()
    
    # Move the child object to the new collection
    for col in child.users_collection:
        col.objects.unlink(child)
    collection.objects.link(child)

    # Set the child's location to (0, 0, 0)
    child.location = (0, 0, 0)
    
    # Create a collection instance in the original location
    instance = bpy.data.objects.new(child_name + "_Instance", None)
    instance.instance_type = 'COLLECTION'
    instance.instance_collection = collection
    instance.location = original_location
    
    # Link the instance to the active collection
    bpy.context.scene.collection.objects.link(instance)

print("Operation completed successfully.")