from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QCursor
from OpenGL.GL import *
from OpenGL.arrays import vbo
import numpy as np
from pygltflib import GLTF2
import trimesh
from PIL import Image
import os
import urllib.parse
import json

class ModelViewer(QOpenGLWidget):
    def __init__(self, model_path, part_visibility=None):
        super().__init__()
        self.model_path = model_path
        self.mesh = None
        self.meshes = []  # List to store multiple meshes or parts
        self.texture_ids = {}  # Dictionary to store texture IDs
        self.material_map = {}  # Maps mesh parts to their materials/textures
        self.rotation_x = 30
        self.rotation_y = 30
        self.translate_x = 0.0
        self.translate_y = 0.0
        self.last_pos = None
        self.zoom = -5.0
        
        # Animation properties
        self.animations = []
        self.current_animation = None
        self.animation_time = 0
        self.is_animating = False
        
        # Part visibility
        self.part_visibility = {int(k): v for k, v in (part_visibility or {}).items()}
        self.part_names = {}
        
        # VBO objects
        self.vertex_vbos = {}  # Dictionary to store VBOs for different parts
        self.uv_vbos = {}
        self.normal_vbos = {}
        self.index_buffers = {}
        self.num_faces = {}

    def initializeGL(self):
        """Initialize OpenGL settings."""
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glClearColor(0, 0, 0, 0)  # Transparent background
        print(f"Before load_model in initializeGL, part_visibility: {self.part_visibility}")
        self.load_model(self.model_path)
        print(f"After load_model in initializeGL, part_visibility: {self.part_visibility}")

    def resizeGL(self, w, h):
        """Handle window resizing."""
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = w / h if h > 0 else 1
        glFrustum(-aspect, aspect, -1.0, 1.0, 2.0, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        """Render the 3D model using optimized rendering."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Zoom and Move Camera
        glTranslatef(self.translate_x, self.translate_y, self.zoom)
        
        # Apply rotation
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_y, 0, 1, 0)
        
        # Apply animations if active
        if self.is_animating and self.current_animation:
            self.apply_animation()
        
        # Render each mesh part
        if self.meshes:
            for part_id, mesh in enumerate(self.meshes):
                # Skip if part is hidden
                if not self.part_visibility.get(part_id, True):
                    continue
                
                # Check if part has VBOs
                if part_id in self.vertex_vbos:
                    self.render_part_with_vbos(part_id)
                else:
                    self.render_part_legacy(part_id, mesh)
        # Fallback to single mesh rendering
        elif self.vertex_vbos.get(0) is not None:
            self.render_part_with_vbos(0)
        elif self.mesh is not None:
            self.render_part_legacy(0, self.mesh)

    def render_part_with_vbos(self, part_id):
        """Render a specific part using VBOs with texture mapping."""
        # Get the texture ID for this part
        texture_id = self.material_map.get(part_id, None)
        
        # Bind texture if available
        if texture_id is not None and texture_id in self.texture_ids:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.texture_ids[texture_id])
            # print(f"Binding texture ID: {self.texture_ids[texture_id]} for part {part_id}")
        else:
            glDisable(GL_TEXTURE_2D)
            # print(f"No texture available for part {part_id}")

        # Enable arrays
        glEnableClientState(GL_VERTEX_ARRAY)
        if part_id in self.normal_vbos and self.normal_vbos[part_id] is not None:
            glEnableClientState(GL_NORMAL_ARRAY)
        if part_id in self.uv_vbos and self.uv_vbos[part_id] is not None and texture_id is not None:
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)

        # Bind and set up arrays
        if part_id in self.vertex_vbos and self.vertex_vbos[part_id] is not None:
            self.vertex_vbos[part_id].bind()
            glVertexPointer(3, GL_FLOAT, 0, None)

        if part_id in self.normal_vbos and self.normal_vbos[part_id] is not None:
            self.normal_vbos[part_id].bind()
            glNormalPointer(GL_FLOAT, 0, None)

        if part_id in self.uv_vbos and self.uv_vbos[part_id] is not None and texture_id is not None:
            self.uv_vbos[part_id].bind()
            glTexCoordPointer(2, GL_FLOAT, 0, None)

        # Draw the triangles
        if part_id in self.index_buffers and self.index_buffers[part_id] is not None:
            glDrawElements(GL_TRIANGLES, self.num_faces.get(part_id, 0) * 3, GL_UNSIGNED_INT, self.index_buffers[part_id])
        else:
            # Fallback to drawing arrays if index buffer isn't available
            glDrawArrays(GL_TRIANGLES, 0, self.num_faces.get(part_id, 0) * 3)

        # Disable arrays
        glDisableClientState(GL_VERTEX_ARRAY)
        if part_id in self.normal_vbos and self.normal_vbos[part_id] is not None:
            glDisableClientState(GL_NORMAL_ARRAY)
        if part_id in self.uv_vbos and self.uv_vbos[part_id] is not None and texture_id is not None:
            glDisableClientState(GL_TEXTURE_COORD_ARRAY)

        # Unbind VBOs safely
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisable(GL_TEXTURE_2D)

    def render_part_legacy(self, part_id, mesh):
        """Fallback rendering method for a specific part using legacy OpenGL."""
        if mesh is None:
            return
            
        # Get the texture ID for this part
        texture_id = self.material_map.get(part_id, None)
        
        # Bind texture if available
        if texture_id is not None and texture_id in self.texture_ids:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.texture_ids[texture_id])
        else:
            glDisable(GL_TEXTURE_2D)
            
        # Get vertices and faces
        vertices = mesh.vertices
        faces = mesh.faces
        
        # Get UV coordinates if available
        has_uv = hasattr(mesh.visual, 'uv')
        uv = mesh.visual.uv if has_uv else None
        
        # Get normals if available
        has_normals = hasattr(mesh, 'vertex_normals')
        normals = mesh.vertex_normals if has_normals else None
        
        # Render using legacy OpenGL
        glBegin(GL_TRIANGLES)
        for face_idx, face in enumerate(faces):
            for i, vertex_idx in enumerate(face):
                if has_normals:
                    glNormal3f(*normals[vertex_idx])
                    
                if has_uv and uv is not None and vertex_idx < len(uv):
                    glTexCoord2f(uv[vertex_idx][0], uv[vertex_idx][1])
                    
                glVertex3f(*vertices[vertex_idx])
        glEnd()
        
        glDisable(GL_TEXTURE_2D)

    def load_model(self, path):
        """Load model with proper clearing and visibility handling."""
        try:
            print(f"Loading model from: {path}")
            if not os.path.exists(path):
                print(f"Model file not found: {path}")
                return

            # Store original visibility and check if it’s the same model
            original_visibility = {int(k): v for k, v in self.part_visibility.items()}
            is_same_model = path == self.model_path
            print(f"Original part_visibility before clearing: {self.part_visibility}, is_same_model: {is_same_model}")

            # Clear old model data
            print("Clearing old model data...")
            self.clear_model_data()
            self.model_path = path
            print(f"Set model_path to: {self.model_path}")

            if path.lower().endswith(('.gltf', '.glb')):
                print("Attempting to load GLTF/GLB model...")
                self.load_gltf_model(path)
            else:
                print("Attempting to load non-GLTF model with trimesh...")
                self.mesh = trimesh.load(path, force='mesh')
                print("Mesh loaded, checking validity...")
                if self.mesh is None:
                    print("Failed to load mesh")
                    return
                print(f"Loaded mesh with {len(self.mesh.vertices)} vertices and {len(self.mesh.faces)} faces")
                if len(self.mesh.vertices) > 10000:
                    print("Large model detected, attempting to simplify...")
                    self.simplify_model(self.mesh)
                model_dir = os.path.dirname(path)
                print(f"Loading textures from directory: {model_dir}")
                self.load_generic_textures(model_dir)
                print("Creating VBOs for part 0...")
                self.create_vbos_for_part(0, self.mesh)
                print("Scaling model...")
                self.scale_model()

            # Apply visibility settings after loading
            print(f"Before apply_visibility_settings, part_visibility: {self.part_visibility}")
            self.apply_visibility_settings(original_visibility, is_same_model)
            print(f"After apply_visibility_settings, part_visibility: {self.part_visibility}")
            self.update()
        except Exception as e:
            import traceback
            print(f"Error loading model: {e}")
            print(f"Exception type: {type(e).__name__}")
            print(f"Full traceback: {traceback.format_exc()}")
            
    def load_gltf_model(self, path):
        """Load and process GLTF/GLB model with multiple meshes and textures."""
        try:
            gltf = GLTF2().load(path)
            model_dir = os.path.dirname(path)
            print(f"Loading GLTF/GLB model: {path}")
            self.load_gltf_textures(path, model_dir)
            
            if not hasattr(gltf, 'meshes') or not gltf.meshes:
                print("No meshes found in GLTF/GLB file")
                return
                
            for mesh_idx, gltf_mesh in enumerate(gltf.meshes):
                for prim_idx, primitive in enumerate(gltf_mesh.primitives):
                    part_id = len(self.meshes)
                    material_idx = getattr(primitive, 'material', None)
                    if material_idx is not None:
                        self.material_map[part_id] = material_idx
                    mesh = self.extract_primitive_mesh(gltf, primitive)
                    if mesh:
                        mesh_name = gltf_mesh.name if gltf_mesh.name else f"Mesh_{mesh_idx}_Prim_{prim_idx}"
                        self.part_names[part_id] = mesh_name
                        self.meshes.append(mesh)
                        # Set default visibility to True if not already set
                        if part_id not in self.part_visibility:
                            self.part_visibility[part_id] = True
                        self.create_vbos_for_part(part_id, mesh)
                        print(f"Loaded mesh part {part_id} named '{mesh_name}' with material {material_idx}")
            
            if self.meshes:
                self.mesh = self.meshes[0]
                self.scale_model()
                self.load_animations(gltf)
        except Exception as e:
            print(f"Error loading GLTF model: {e}")

    def clear_model_data(self):
        self.mesh = None
        self.meshes.clear()
        for tex_id in self.texture_ids.values():
            if tex_id:
                glDeleteTextures([tex_id])
        self.texture_ids.clear()
        self.material_map.clear()
        for vbo in self.vertex_vbos.values():
            if vbo is not None:
                vbo.delete()
        self.vertex_vbos.clear()
        for vbo in self.uv_vbos.values():
            if vbo is not None:
                vbo.delete()
        self.uv_vbos.clear()
        for vbo in self.normal_vbos.values():
            if vbo is not None:
                vbo.delete()
        self.normal_vbos.clear()
        self.index_buffers.clear()
        self.num_faces.clear()
        self.part_names.clear()
        self.part_visibility = {}
        print(f"After clear_model_data, part_visibility: {self.part_visibility}")

    def apply_visibility_settings(self, original_visibility, is_same_model):
        """Apply visibility settings based on whether it’s the same model or a new one."""
        current_parts = set(range(len(self.meshes)))
        config_parts = set(int(k) for k in original_visibility.keys())
        
        if is_same_model:
            # Same model: preserve original visibility where possible
            for part_id in current_parts:
                if part_id in original_visibility:
                    self.part_visibility[part_id] = original_visibility[part_id]
                    print(f"Preserved visibility for part {part_id} (same model): {self.part_visibility[part_id]}")
                else:
                    self.part_visibility[part_id] = True
                    print(f"Set default visibility for new part {part_id} (same model): True")
        else:
            # New model: apply config visibility if available, otherwise default to True
            for part_id in current_parts:
                if part_id in original_visibility:
                    self.part_visibility[part_id] = original_visibility[part_id]
                    print(f"Applied config visibility for part {part_id} (new model): {self.part_visibility[part_id]}")
                else:
                    self.part_visibility[part_id] = True
                    print(f"Set default visibility for part {part_id} (new model): True")
            
            # Remove obsolete parts from visibility
            for part_id in config_parts - current_parts:
                self.part_visibility.pop(part_id, None)
                print(f"Removed visibility for obsolete part {part_id} (new model)")

    def extract_primitive_mesh(self, gltf, primitive):
        """Extract a trimesh.Trimesh object from a GLTF primitive."""
        try:
            # Check if there are buffers and buffer views
            if not gltf.buffers or not gltf.bufferViews:
                print("No buffer data available in GLTF file")
                return None

            # Determine if this is a GLB file (binary buffer) or GLTF (external buffer)
            model_dir = os.path.dirname(self.model_path)
            if gltf.buffers[0].uri is None:
                # GLB case: binary data is embedded
                buffer_data = gltf.binary_blob()
                if buffer_data is None:
                    print("Expected binary blob for GLB file, but none found")
                    return None
            else:
                # GLTF case: load external buffer file
                buffer_uri = gltf.buffers[0].uri
                buffer_path = os.path.join(model_dir, buffer_uri)
                if not os.path.exists(buffer_path):
                    print(f"External buffer file not found: {buffer_path}")
                    return None
                with open(buffer_path, 'rb') as f:
                    buffer_data = f.read()

            # Extract vertex positions (required)
            if not hasattr(primitive.attributes, 'POSITION') or primitive.attributes.POSITION is None:
                print("Primitive has no POSITION attribute")
                return None

            pos_accessor = gltf.accessors[primitive.attributes.POSITION]
            pos_buffer_view = gltf.bufferViews[pos_accessor.bufferView]
            pos_offset = pos_buffer_view.byteOffset + (pos_accessor.byteOffset or 0)
            pos_count = pos_accessor.count
            pos_type = pos_accessor.componentType  # e.g., GL_FLOAT (5126)
            pos_size = 3  # Assuming vec3 for positions

            # Read vertex positions
            dtype = np.float32 if pos_type == 5126 else np.float16
            pos_bytes = buffer_data[pos_offset:pos_offset + pos_buffer_view.byteLength]
            vertices = np.frombuffer(pos_bytes, dtype=dtype).reshape(pos_count, pos_size)

            # Extract faces (indices)
            faces = None
            if primitive.indices is not None:
                idx_accessor = gltf.accessors[primitive.indices]
                idx_buffer_view = gltf.bufferViews[idx_accessor.bufferView]
                idx_offset = idx_buffer_view.byteOffset + (idx_accessor.byteOffset or 0)
                idx_count = idx_accessor.count
                idx_type = idx_accessor.componentType  # e.g., GL_UNSIGNED_INT (5125)

                # Read indices
                dtype = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32}.get(idx_type, np.uint32)
                idx_bytes = buffer_data[idx_offset:idx_offset + idx_buffer_view.byteLength]
                indices = np.frombuffer(idx_bytes, dtype=dtype)
                faces = indices.reshape(-1, 3)  # Assuming triangles

            # Extract normals (optional)
            normals = None
            if hasattr(primitive.attributes, 'NORMAL') and primitive.attributes.NORMAL is not None:
                norm_accessor = gltf.accessors[primitive.attributes.NORMAL]
                norm_buffer_view = gltf.bufferViews[norm_accessor.bufferView]
                norm_offset = norm_buffer_view.byteOffset + (norm_accessor.byteOffset or 0)
                norm_count = norm_accessor.count

                norm_bytes = buffer_data[norm_offset:norm_offset + norm_buffer_view.byteLength]
                normals = np.frombuffer(norm_bytes, dtype=np.float32).reshape(norm_count, 3)

            # Extract UV coordinates (optional)
            uv = None
            if hasattr(primitive.attributes, 'TEXCOORD_0') and primitive.attributes.TEXCOORD_0 is not None:
                uv_accessor = gltf.accessors[primitive.attributes.TEXCOORD_0]
                uv_buffer_view = gltf.bufferViews[uv_accessor.bufferView]
                uv_offset = uv_buffer_view.byteOffset + (uv_accessor.byteOffset or 0)
                uv_count = uv_accessor.count

                uv_bytes = buffer_data[uv_offset:uv_offset + uv_buffer_view.byteLength]
                uv = np.frombuffer(uv_bytes, dtype=np.float32).reshape(uv_count, 2)
                # Make a writable copy before modifying
                uv = uv.copy()
                # Flip Y coordinate to match OpenGL convention
                uv[:, 1] = 1.0 - uv[:, 1]

            # Create trimesh object
            mesh = trimesh.Trimesh(
                vertices=vertices,
                faces=faces if faces is not None else None,
                vertex_normals=normals,
                process=False  # Avoid unnecessary processing
            )

            # Attach UV coordinates if present
            if uv is not None:
                mesh.visual = trimesh.visual.TextureVisuals(uv=uv)

            print(f"Extracted primitive: vertices={len(vertices)}, faces={len(faces) if faces is not None else 0}")
            return mesh

        except Exception as e:
            print(f"Error extracting primitive mesh: {e}")
            return None
    
    def load_animations(self, gltf):
        """Load animations from GLTF file."""
        if not hasattr(gltf, 'animations') or not gltf.animations:
            print("No animations found in GLTF file")
            return
            
        print(f"Found {len(gltf.animations)} animations")
        
        # For now, just store the animation data 
        # Implementation will be expanded later
        self.animations = gltf.animations
        
    def apply_animation(self):
        """Apply the current animation to the model."""
        # This is a placeholder for animation implementation
        # Will be expanded in the future
        pass
            
    def simplify_model(self, mesh):
        """Simplify the model using available Trimesh methods."""
        try:
            print("Attempting to simplify model...")

            # Safety check
            if mesh is None or not hasattr(mesh, 'vertices'):
                print("No valid mesh to simplify")
                return

            # Simple approach: subsample vertices
            if len(mesh.vertices) > 10000:
                target_faces = int(len(mesh.faces) * 0.5)  # Reduce by half

                # Try different simplification methods
                if hasattr(mesh, 'simplify'):
                    print("Using mesh.simplify method")
                    mesh = mesh.simplify(target_faces)
                elif hasattr(trimesh, 'simplify'):
                    print("Using trimesh.simplify method")
                    mesh = trimesh.simplify.simplify_quadratic_decimation(mesh, target_faces)
                else:
                    print("No simplification method available")

                print(f"Model simplified to {len(mesh.vertices)} vertices")
                return mesh
            return mesh
        except Exception as e:
            print(f"Error simplifying model: {e}")
            # Keep the original model if simplification fails
            return mesh
        
    def create_vbos_for_part(self, part_id, mesh):
        """Create Vertex Buffer Objects for efficient rendering of a specific part."""
        try:
            if mesh is None:
                return

            # Create VBO for vertices
            vertices = np.array(mesh.vertices, dtype=np.float32)
            self.vertex_vbos[part_id] = vbo.VBO(vertices)

            # Create VBO for normals if available
            if hasattr(mesh, 'vertex_normals') and mesh.vertex_normals is not None:
                normals = np.array(mesh.vertex_normals, dtype=np.float32)
                self.normal_vbos[part_id] = vbo.VBO(normals)
            else:
                self.normal_vbos[part_id] = None

            # Create VBO for texture coordinates if available
            self.uv_vbos[part_id] = None
            if hasattr(mesh, 'visual') and hasattr(mesh.visual, 'uv'):
                if mesh.visual.uv is not None and len(mesh.visual.uv) > 0:
                    uvs = np.array(mesh.visual.uv, dtype=np.float32)
                    # Flip Y coordinates if needed
                    # uvs[:, 1] = 1.0 - uvs[:, 1]  # Uncomment this if textures appear upside down
                    self.uv_vbos[part_id] = vbo.VBO(uvs)
                    print(f"Created UV VBO for part {part_id} with {len(uvs)} coordinates")
                else:
                    print(f"Part {part_id} has UV attribute but no UV data")
            else:
                print(f"Part {part_id} has no UV coordinates")

            # Create index buffer
            if hasattr(mesh, 'faces') and mesh.faces is not None:
                self.index_buffers[part_id] = np.array(mesh.faces, dtype=np.uint32).flatten()
                self.num_faces[part_id] = len(mesh.faces)
            else:
                self.index_buffers[part_id] = None
                self.num_faces[part_id] = 0

            print(f"VBOs created successfully for part {part_id}: vertices={len(vertices)}, faces={self.num_faces[part_id]}")
        except Exception as e:
            print(f"Error creating VBOs for part {part_id}: {e}")
            self.vertex_vbos[part_id] = None
            self.normal_vbos[part_id] = None
            self.uv_vbos[part_id] = None
            self.index_buffers[part_id] = None

    def load_gltf_textures(self, path, model_dir):
        """Load textures from GLTF file with improved error handling."""
        try:
            gltf = GLTF2().load(path)
            texture_count = 0

            # Print path for debugging
            print(f"Loading textures from: {path}")
            print(f"Model directory: {model_dir}")

            # Process materials to understand texture usage
            if hasattr(gltf, 'materials') and gltf.materials:
                print(f"Found {len(gltf.materials)} materials")
                for material_idx, material in enumerate(gltf.materials):
                    # Check for textures in this material
                    if hasattr(material, 'pbrMetallicRoughness'):
                        pbr = material.pbrMetallicRoughness
                        
                        # Base color texture
                        if hasattr(pbr, 'baseColorTexture') and pbr.baseColorTexture is not None:
                            if hasattr(pbr.baseColorTexture, 'index'):
                                texture_idx = pbr.baseColorTexture.index
                                print(f"Material {material_idx} uses texture {texture_idx} for baseColor")
                        
                        # Metallic roughness texture
                        if hasattr(pbr, 'metallicRoughnessTexture') and pbr.metallicRoughnessTexture is not None:
                            if hasattr(pbr.metallicRoughnessTexture, 'index'):
                                texture_idx = pbr.metallicRoughnessTexture.index
                                print(f"Material {material_idx} uses texture {texture_idx} for metallicRoughness")
                    
                    # Normal map
                    if hasattr(material, 'normalTexture') and material.normalTexture is not None:
                        if hasattr(material.normalTexture, 'index'):
                            texture_idx = material.normalTexture.index
                            print(f"Material {material_idx} uses texture {texture_idx} for normal")
                    
                    # Emissive texture
                    if hasattr(material, 'emissiveTexture') and material.emissiveTexture is not None:
                        if hasattr(material.emissiveTexture, 'index'):
                            texture_idx = material.emissiveTexture.index
                            print(f"Material {material_idx} uses texture {texture_idx} for emissive")
                    
                    # Occlusion texture
                    if hasattr(material, 'occlusionTexture') and material.occlusionTexture is not None:
                        if hasattr(material.occlusionTexture, 'index'):
                            texture_idx = material.occlusionTexture.index
                            print(f"Material {material_idx} uses texture {texture_idx} for occlusion")

            # Process textures
            if hasattr(gltf, 'textures') and gltf.textures:
                print(f"Found {len(gltf.textures)} textures")
                for texture_idx, texture in enumerate(gltf.textures):
                    if hasattr(texture, 'source') and texture.source is not None:
                        image_idx = texture.source
                        print(f"Texture {texture_idx} uses image {image_idx}")

            # Handle external textures
            if hasattr(gltf, 'images') and gltf.images:
                print(f"Found {len(gltf.images)} images")
                for image_idx, image in enumerate(gltf.images):
                    if hasattr(image, 'uri') and image.uri:
                        # Skip data URIs
                        if image.uri.startswith('data:'):
                            continue

                        decoded_uri = urllib.parse.unquote(image.uri)
                        print(f"Image {image_idx} - Original URI: {image.uri}")
                        print(f"Image {image_idx} - Decoded URI: {decoded_uri}")

                        # Construct full path to texture
                        image_path = os.path.join(model_dir, decoded_uri)
                        print(f"Looking for texture at: {image_path}")

                        # Check if file exists
                        if os.path.exists(image_path):
                            print(f"Found texture file: {image_path}")
                            texture_id = self.load_texture(image_path)
                            if texture_id:
                                self.texture_ids[image_idx] = texture_id
                                texture_count += 1
                        else:
                            print(f"Texture file not found: {image_path}")

            # If this is a GLB file, try to extract embedded textures
            if path.lower().endswith('.glb'):
                print("Trying to extract embedded textures from GLB file")
                try:
                    # Create a temporary directory for extracting textures
                    import tempfile
                    temp_dir = tempfile.mkdtemp()

                    # Use existing gltf object instead of reloading
                    if hasattr(gltf, 'export_textures'):
                        gltf.export_textures(temp_dir)

                        # Find all extracted textures
                        for i, texture_file in enumerate(os.listdir(temp_dir)):
                            texture_path = os.path.join(temp_dir, texture_file)
                            print(f"Found embedded texture: {texture_path}")
                            texture_id = self.load_texture(texture_path)
                            if texture_id:
                                self.texture_ids[i] = texture_id
                                texture_count += 1

                        # Cleanup temp directory
                        import shutil
                        shutil.rmtree(temp_dir)
                    else:
                        print("GLTF object does not support export_textures method")
                except Exception as e:
                    print(f"Error extracting GLB textures: {e}")

            print(f"Successfully loaded {texture_count} textures from GLTF/GLB")
        except Exception as e:
            print(f"Error loading GLTF textures: {e}")

    def load_generic_textures(self, model_dir):
        """Load textures for non-GLTF models."""
        if hasattr(self.mesh, 'visual') and hasattr(self.mesh.visual, 'material'):
            if hasattr(self.mesh.visual.material, 'image'):
                image = self.mesh.visual.material.image
                if isinstance(image, str):
                    image_path = os.path.join(model_dir, image)
                    if os.path.exists(image_path):
                        texture_id = self.load_texture(image_path)
                        self.texture_ids[0] = texture_id
                        self.material_map[0] = 0  # Map the first part to the first texture
                elif hasattr(image, 'convert'):
                    texture_id = self.create_texture_from_image(image)
                    self.texture_ids[0] = texture_id
                    self.material_map[0] = 0  # Map the first part to the first texture

    def load_texture(self, path):
        """Load a texture from file with better error handling."""
        try:
            print(f"Loading texture from: {path}")

            # Check if file exists
            if not os.path.exists(path):
                print(f"Texture file not found: {path}")
                return None

            # Try to open the image
            try:
                image = Image.open(path)
            except Exception as e:
                print(f"Failed to open image: {e}")
                return None

            # Convert to RGBA if needed
            if image.mode != 'RGBA':
                image = image.convert('RGBA')

            image = image.transpose(Image.FLIP_TOP_BOTTOM)

            # Resize large textures to improve performance
            max_size = 1024
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Create OpenGL texture
            texture_id = self.create_texture_from_image(image)
            print(f"Created texture ID: {texture_id}")
            return texture_id
        except Exception as e:
            print(f"Error loading texture {path}: {e}")
            return None

    def create_texture_from_image(self, image):
        """Create an OpenGL texture from a PIL Image."""
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        
        # Set better texture parameters
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        
        # Convert image to bytes and upload to GPU
        img_data = np.array(image)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA, 
            image.width, image.height, 0, 
            GL_RGBA, GL_UNSIGNED_BYTE, img_data
        )
        
        # Generate mipmaps
        try:
            glGenerateMipmap(GL_TEXTURE_2D)
        except:
            # Fallback for older OpenGL versions
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        
        return texture_id

    def scale_model(self):
        """Scale all meshes to fit the view."""
        if not self.meshes:
            return
        
        # Find the overall bounds of all meshes
        all_vertices = np.vstack([mesh.vertices for mesh in self.meshes if hasattr(mesh, 'vertices')])
        if len(all_vertices) == 0:
            return
            
        min_bounds = np.min(all_vertices, axis=0)
        max_bounds = np.max(all_vertices, axis=0)
        bounds = np.vstack((min_bounds, max_bounds))
        
        size_range = bounds[1] - bounds[0]
        if np.max(size_range) == 0:
            return
            
        # Use a larger scale factor for a bigger model
        scale = 4.0 / max(size_range)
        
        # Calculate the centroid of all vertices
        centroid = np.mean(all_vertices, axis=0)
        
        # Scale and center each mesh
        for part_id, mesh in enumerate(self.meshes):
            if hasattr(mesh, 'vertices') and len(mesh.vertices) > 0:
                # Apply scaling
                mesh.vertices *= scale
                
                # Center the model
                mesh.vertices -= centroid * scale
                
                # Update VBOs after scaling
                if part_id in self.vertex_vbos and self.vertex_vbos[part_id] is not None:
                    self.create_vbos_for_part(part_id, mesh)

    def mousePressEvent(self, event):
        """Handle mouse press events for model interaction."""
        self.last_pos = event.position()

    def mouseMoveEvent(self, event):
        """Handle mouse movement events for rotation and panning."""
        if self.last_pos is None:
            self.last_pos = event.position()
            return
            
        dx = event.position().x() - self.last_pos.x()
        dy = event.position().y() - self.last_pos.y()
        
        if event.buttons() & Qt.MouseButton.LeftButton:
            # Left mouse: Rotate
            self.rotation_y += dx * 0.5
            self.rotation_x += dy * 0.5
            self.update()
        elif event.buttons() & Qt.MouseButton.MiddleButton:
            # Middle mouse: Pan
            self.translate_x += dx * 0.01
            self.translate_y -= dy * 0.01
            self.update()
        
        self.last_pos = event.position()

    def wheelEvent(self, event):
        """Add zooming capability with mouse wheel."""
        delta = event.angleDelta().y()
        self.zoom += delta * 0.01
        self.update()
    
    def sizeHint(self):
        """Provide a default size for the widget."""
        return QSize(400, 400)
        
    def minimumSizeHint(self):
        """Provide a minimum size for the widget."""
        return QSize(200, 200)
        
    def toggle_wireframe(self, enable=None):
        """Toggle wireframe rendering mode."""
        if enable is None:
            # Toggle current state
            if glIsEnabled(GL_POLYGON_OFFSET_FILL):
                glDisable(GL_POLYGON_OFFSET_FILL)
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            else:
                glEnable(GL_POLYGON_OFFSET_FILL)
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        else:
            # Set specified state
            if enable:
                glDisable(GL_POLYGON_OFFSET_FILL)
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            else:
                glEnable(GL_POLYGON_OFFSET_FILL)
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        self.update()
        
    def use_point_cloud(self, enable=None):
        """Toggle point cloud rendering mode for very large models."""
        if enable is None:
            # Toggle current state
            if glGetIntegerv(GL_POLYGON_MODE) == GL_POINT:
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            else:
                glPolygonMode(GL_FRONT_AND_BACK, GL_POINT)
                glPointSize(3.0)
        else:
            # Set specified state
            if enable:
                glPolygonMode(GL_FRONT_AND_BACK, GL_POINT)
                glPointSize(3.0)
            else:
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        self.update()
    
    def enterEvent(self, event):
        self.unsetCursor()

    def leaveEvent(self, event):
        self.unsetCursor()