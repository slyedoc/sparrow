import bpy
import bmesh

# Function to compare two mesh objects by their geometry (vertex, edge, and face count)
def compare_meshes(obj1, obj2):
    if len(obj1.data.vertices) != len(obj2.data.vertices):
        return False
    if len(obj1.data.edges) != len(obj2.data.edges):
        return False
    if len(obj1.data.polygons) != len(obj2.data.polygons):
        return False

    # Optional: Compare material slots
    if len(obj1.material_slots) != len(obj2.material_slots):
        return False
    
    # Compare each material in the slots
    for mat1, mat2 in zip(obj1.material_slots, obj2.material_slots):
        if mat1.material != mat2.material:
            return False 

#    # Compare geometry by creating BMesh instances for each object
#    bm1 = bmesh.new()
#    bm2 = bmesh.new()

#    bm1.from_mesh(obj1.data)
#    bm2.from_mesh(obj2.data)

#    # Check vertex coordinates
#    for v1, v2 in zip(bm1.verts, bm2.verts):
#        if (v1.co - v2.co).length > 1e-6:  # Small tolerance for floating point precision
#            bm1.free()
#            bm2.free()
#            return False

#    # Clean up BMesh instances
#    bm1.free()
#    bm2.free()

    return True

# Function to find duplicates by comparing geometry
def find_geometry_duplicates():
    duplicates = {}
    
    # Iterate over all mesh objects in the scene
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            # Compare this object against all previous ones to find duplicates
            for key in duplicates:
                if compare_meshes(obj, key):
                    duplicates[key].append(obj)
                    break
            else:
                duplicates[obj] = [obj]

    # figure out the base object based on the lowest Y value
    rekey = []
    for key, duplicate_objs in duplicates.items():
        # see which is farther in -Y
        farthest_obj = min(duplicate_objs, key=lambda obj: obj.location.y)
        if farthest_obj.location.y < key.location.y:
            rekey.append((key, farthest_obj))

    for key, farthest_obj in rekey:
        dups = duplicates.pop(key)      
        dups.remove(farthest_obj)
        dups.append(key)  
        duplicates[farthest_obj] = dups
        
    return duplicates

def create_collection_for_item(duplicate_objs):
    # Create a collection for the first object and call it "Item_<name>"
    original_obj = duplicate_objs[0]
    item_collection = bpy.data.collections.new(f"Item_{original_obj.name}")
    bpy.context.scene.collection.children.link(item_collection)
    
    # Move the original object to the new collection
    bpy.context.scene.collection.objects.unlink(original_obj)
    item_collection.objects.link(original_obj)
    
    # Create collection instances for other duplicates
    for dup_obj in duplicate_objs[1:]:
        # Create a collection instance
        instance = bpy.data.objects.new(f"{dup_obj.name}_instance", None)
        instance.instance_type = 'COLLECTION'
        instance.instance_collection = item_collection
        
        # Preserve location, rotation, and scale
        instance.location = dup_obj.location
        instance.rotation_euler = dup_obj.rotation_euler
        instance.scale = dup_obj.scale
        
        # Link the instance to the scene
        bpy.context.scene.collection.objects.link(instance)
        
        # Remove the original duplicate object
        bpy.context.scene.collection.objects.unlink(dup_obj)
        bpy.data.objects.remove(dup_obj)

def main():
    duplicates = find_geometry_duplicates()
    
    # For each set of duplicates, create a collection and replace duplicates with collection instances
    for key, duplicate_objs in duplicates.items():
        if len(duplicate_objs) > 1:  # Only process if there are duplicates            
        #    create_collection_for_item(duplicate_objs)
            print(f"{key.name} - {len(duplicate_objs)}")
            for d in duplicate_objs:
                print(f"\t{d.name}")

# Run the script
main()