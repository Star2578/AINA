from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QCursor
from OpenGL.GL import *
from OpenGL.arrays import vbo
import numpy as np
from pygltflib import GLTF2
from PIL import Image
import os
import urllib.parse
import io
import struct

class ModelViewer(QOpenGLWidget):
    def __init__(self, model_path, part_visibility=None):
        super().__init__()
        self.model_path = model_path
        self.meshes = []  # List to store multiple meshes or parts
        self.texture_ids = {}  # Dictionary to store texture IDs
        self.material_map = {}  # Maps mesh parts to their materials/textures
        self.rotation_x = 30
        self.rotation_y = 30
        self.translate_x = 0.0
        self.translate_y = 0.0
        self.last_pos = None
        self.zoom = -4.0
        
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
            for part_id in range(len(self.meshes)):
                # Skip if part is hidden
                if not self.part_visibility.get(part_id, True):
                    continue
                
                # Check if part has VBOs
                if part_id in self.vertex_vbos:
                    self.render_part_with_vbos(part_id)

    def render_part_with_vbos(self, part_id):
        """Render a specific part using VBOs with texture mapping."""
        # Get the texture ID for this part
        texture_id = self.material_map.get(part_id, None)
        
        # Bind texture if available
        if texture_id is not None and texture_id in self.texture_ids:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.texture_ids[texture_id])
        else:
            glDisable(GL_TEXTURE_2D)

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

    def load_model(self, path):
        """Load model with proper clearing and visibility handling."""
        try:
            print(f"Loading model from: {path}")
            if not os.path.exists(path):
                print(f"Model file not found: {path}")
                return

            # Store original visibility and check if it's the same model
            original_visibility = {int(k): v for k, v in self.part_visibility.items()}
            is_same_model = path == self.model_path
            print(f"Original part_visibility before clearing: {self.part_visibility}, is_same_model: {is_same_model}")

            # Clear old model data
            print("Clearing old model data...")
            self.clear_model_data()
            self.model_path = path
            print(f"Set model_path to: {self.model_path}")

            # Only support GLTF/GLB files now
            if path.lower().endswith(('.gltf', '.glb')):
                print("Loading GLTF/GLB model...")
                self.load_gltf_model(path)
            else:
                print("Only GLTF/GLB models are supported")
                return

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
            self.load_gltf_textures(gltf, path, model_dir)
            
            if not hasattr(gltf, 'meshes') or not gltf.meshes:
                print("No meshes found in GLTF/GLB file")
                return
                
            for mesh_idx, gltf_mesh in enumerate(gltf.meshes):
                for prim_idx, primitive in enumerate(gltf_mesh.primitives):
                    part_id = len(self.meshes)
                    material_idx = getattr(primitive, 'material', None)
                    if material_idx is not None:
                        self.material_map[part_id] = material_idx
                    
                    mesh_data = {
                        'primitive': primitive,
                        'gltf': gltf,
                        'mesh_idx': mesh_idx,
                        'prim_idx': prim_idx
                    }
                    mesh_name = gltf_mesh.name if gltf_mesh.name else f"Mesh_{mesh_idx}_Prim_{prim_idx}"
                    self.part_names[part_id] = mesh_name
                    self.meshes.append(mesh_data)
                    
                    if part_id not in self.part_visibility:
                        self.part_visibility[part_id] = True
                    
                    self.process_primitive_to_vbo(part_id, gltf, primitive)
                    print(f"Loaded mesh part {part_id} named '{mesh_name}' with material {material_idx}")
            
            if self.meshes:
                self.scale_model()
                self.load_animations(gltf)
        except Exception as e:
            import traceback
            print(f"Error loading GLTF model: {e}")
            print(traceback.format_exc())

    def process_primitive_to_vbo(self, part_id, gltf, primitive):
        """Process a GLTF primitive directly to VBOs without using trimesh."""
        try:
            # Check if the primitive has position attribute (required)
            if not hasattr(primitive.attributes, 'POSITION') or primitive.attributes.POSITION is None:
                print(f"Primitive {part_id} has no POSITION attribute")
                return False
            
            binary_data = None
            if gltf.buffers[0].uri is None:
                # GLB case: binary data is embedded
                binary_data = gltf.binary_blob()
                if binary_data is None:
                    print("Expected binary blob for GLB file, but none found")
                    return False
            else:
                # GLTF case: load external buffer file
                decoded_path = urllib.parse.unquote(self.model_path)
                model_dir = os.path.dirname(decoded_path)
                buffer_uri = gltf.buffers[0].uri
                buffer_uri = urllib.parse.unquote(buffer_uri)
                buffer_path = os.path.join(model_dir, buffer_uri)
                if not os.path.exists(buffer_path):
                    print(f"External buffer file not found: {buffer_path}")
                    return False
                with open(buffer_path, 'rb') as f:
                    binary_data = f.read()
            
            # Extract vertex positions
            pos_accessor = gltf.accessors[primitive.attributes.POSITION]
            vertices = self._extract_accessor_data(gltf, pos_accessor, binary_data, 3)
            if vertices is None:
                print(f"Failed to extract vertex positions for part {part_id}")
                return False
            
            # Create vertex VBO
            self.vertex_vbos[part_id] = vbo.VBO(np.array(vertices, dtype=np.float32))
            
            # Extract normals (optional)
            if hasattr(primitive.attributes, 'NORMAL') and primitive.attributes.NORMAL is not None:
                norm_accessor = gltf.accessors[primitive.attributes.NORMAL]
                normals = self._extract_accessor_data(gltf, norm_accessor, binary_data, 3)
                if normals is not None:
                    self.normal_vbos[part_id] = vbo.VBO(np.array(normals, dtype=np.float32))
                else:
                    self.normal_vbos[part_id] = None
            else:
                self.normal_vbos[part_id] = None
            
            # Extract texture coordinates (optional)
            if hasattr(primitive.attributes, 'TEXCOORD_0') and primitive.attributes.TEXCOORD_0 is not None:
                uv_accessor = gltf.accessors[primitive.attributes.TEXCOORD_0]
                uvs = self._extract_accessor_data(gltf, uv_accessor, binary_data, 2)
                if uvs is not None:
                    # Flip Y coordinates for OpenGL
                    uvs_copy = uvs.copy()
                    uvs_copy[:, 1] = 1.0 - uvs_copy[:, 1]
                    self.uv_vbos[part_id] = vbo.VBO(np.array(uvs_copy, dtype=np.float32))
                else:
                    self.uv_vbos[part_id] = None
            else:
                self.uv_vbos[part_id] = None
            
            # Extract indices (optional)
            if primitive.indices is not None:
                idx_accessor = gltf.accessors[primitive.indices]
                indices = self._extract_accessor_data(gltf, idx_accessor, binary_data, 1)
                if indices is not None:
                    self.index_buffers[part_id] = np.array(indices, dtype=np.uint32).flatten()
                    self.num_faces[part_id] = len(indices) // 3
                else:
                    self.index_buffers[part_id] = None
                    self.num_faces[part_id] = len(vertices) // 3
            else:
                # No indices, assume vertices are already arranged as triangles
                self.index_buffers[part_id] = None
                self.num_faces[part_id] = len(vertices) // 3
            
            print(f"Created VBOs for part {part_id}: vertices={len(vertices)}, faces={self.num_faces[part_id]}")
            return True
        except Exception as e:
            import traceback
            print(f"Error processing primitive to VBO for part {part_id}: {e}")
            print(traceback.format_exc())
            return False

    def _extract_accessor_data(self, gltf, accessor, binary_data, expected_components):
        """Helper method to extract data from a GLTF accessor with proper error handling."""
        try:
            # Get buffer view
            if accessor.bufferView is None:
                print("Accessor has no bufferView")
                return None
                
            buffer_view = gltf.bufferViews[accessor.bufferView]
            
            # Calculate offsets and stride
            byte_offset = (accessor.byteOffset or 0) + (buffer_view.byteOffset or 0)
            byte_stride = buffer_view.byteStride if hasattr(buffer_view, 'byteStride') and buffer_view.byteStride else 0
            component_type = accessor.componentType  # e.g., GL_FLOAT (5126)
            
            # Determine data type and size based on component type
            component_size = 0
            dtype = None
            format_char = ''
            
            if component_type == 5120:  # BYTE
                dtype = np.int8
                component_size = 1
                format_char = 'b'
            elif component_type == 5121:  # UNSIGNED_BYTE
                dtype = np.uint8
                component_size = 1
                format_char = 'B'
            elif component_type == 5122:  # SHORT
                dtype = np.int16
                component_size = 2
                format_char = 'h'
            elif component_type == 5123:  # UNSIGNED_SHORT
                dtype = np.uint16
                component_size = 2
                format_char = 'H'
            elif component_type == 5125:  # UNSIGNED_INT
                dtype = np.uint32
                component_size = 4
                format_char = 'I'
            elif component_type == 5126:  # FLOAT
                dtype = np.float32
                component_size = 4
                format_char = 'f'
            else:
                print(f"Unsupported component type: {component_type}")
                return None
                
            # Calculate element size
            element_size = component_size * expected_components
            
            # Handle stride
            if byte_stride == 0:
                byte_stride = element_size
            
            # More efficient data extraction
            if byte_stride == element_size:
                # If data is tightly packed, we can extract it in one go
                start = byte_offset
                end = start + accessor.count * element_size
                buffer_data = binary_data[start:end]
                
                # If we need to convert from BYTE or SHORT to normalized float
                if accessor.normalized and component_type in [5120, 5121, 5122, 5123]:
                    # Convert to numpy array first
                    array = np.frombuffer(buffer_data, dtype=dtype).reshape(-1, expected_components)
                    
                    # Normalize based on component type
                    if component_type == 5120:  # BYTE: -127 to 127
                        array = array.astype(np.float32) / 127.0
                    elif component_type == 5121:  # UNSIGNED_BYTE: 0 to 255
                        array = array.astype(np.float32) / 255.0
                    elif component_type == 5122:  # SHORT: -32767 to 32767
                        array = array.astype(np.float32) / 32767.0
                    elif component_type == 5123:  # UNSIGNED_SHORT: 0 to 65535
                        array = array.astype(np.float32) / 65535.0
                    
                    return array
                else:
                    # Regular conversion to numpy array
                    return np.frombuffer(buffer_data, dtype=dtype).reshape(-1, expected_components)
            else:
                # If data has stride, extract elements one by one
                data = []
                for i in range(accessor.count):
                    start = byte_offset + i * byte_stride
                    end = start + element_size
                    element_data = binary_data[start:end]
                    if len(element_data) < element_size:
                        print(f"Warning: Data truncated at element {i}, got {len(element_data)} bytes, expected {element_size}")
                        break
                    
                    # Unpack the element data
                    values = struct.unpack(f'{expected_components}{format_char}', element_data)
                    data.append(values)
                
                # Convert to numpy array
                array = np.array(data, dtype=dtype)
                
                # Apply normalization if needed
                if accessor.normalized and component_type in [5120, 5121, 5122, 5123]:
                    if component_type == 5120:  # BYTE
                        array = array.astype(np.float32) / 127.0
                    elif component_type == 5121:  # UNSIGNED_BYTE
                        array = array.astype(np.float32) / 255.0
                    elif component_type == 5122:  # SHORT
                        array = array.astype(np.float32) / 32767.0
                    elif component_type == 5123:  # UNSIGNED_SHORT
                        array = array.astype(np.float32) / 65535.0
                
                return array
            
        except Exception as e:
            import traceback
            print(f"Error in _extract_accessor_data: {e}")
            print(traceback.format_exc())
            return None

    def clear_model_data(self):
        """Clear all model data."""
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
        # Don't clear part_visibility - it will be handled by apply_visibility_settings
        print(f"After clear_model_data, part_visibility: {self.part_visibility}")

    def apply_visibility_settings(self, original_visibility, is_same_model):
        """Apply visibility settings based on whether it's the same model or a new one."""
        current_parts = set(range(len(self.meshes)))
        config_parts = set(int(k) for k in original_visibility.keys())
        
        if is_same_model:
            # Same model: preserve original visibility, only update for current parts
            new_visibility = {}
            for part_id in current_parts:
                if part_id in original_visibility:
                    new_visibility[part_id] = original_visibility[part_id]
                    print(f"Preserved visibility for part {part_id} (same model): {new_visibility[part_id]}")
                else:
                    new_visibility[part_id] = True
                    print(f"Set default visibility for new part {part_id} (same model): True")
            self.part_visibility = new_visibility
        else:
            # New model: reset visibility and apply config settings or defaults
            self.part_visibility = {}
            for part_id in current_parts:
                if part_id in original_visibility:
                    self.part_visibility[part_id] = original_visibility[part_id]
                    print(f"Applied config visibility for part {part_id} (new model): {self.part_visibility[part_id]}")
                else:
                    self.part_visibility[part_id] = True
                    print(f"Set default visibility for part {part_id} (new model): True")
        
        # Log final state
        print(f"Final part_visibility after applying settings: {self.part_visibility}")

    def load_gltf_textures(self, gltf, path, model_dir):
        """Improved method to load textures from GLTF/GLB files."""
        try:
            print(f"Loading textures from: {path}")
            print(f"Model directory: {model_dir}")

            # Check if this is a GLB file
            is_glb = path.lower().endswith('.glb')

            # Create a mapping from texture index to image index
            texture_to_image = {}
            if hasattr(gltf, 'textures') and gltf.textures:
                for texture_idx, texture in enumerate(gltf.textures):
                    if hasattr(texture, 'source') and texture.source is not None:
                        texture_to_image[texture_idx] = texture.source
                        print(f"Texture {texture_idx} uses image {texture.source}")

            # Create a mapping from material index to texture indices
            material_to_textures = {}
            if hasattr(gltf, 'materials') and gltf.materials:
                for material_idx, material in enumerate(gltf.materials):
                    material_to_textures[material_idx] = set()

                    # Check for PBR textures
                    if hasattr(material, 'pbrMetallicRoughness'):
                        pbr = material.pbrMetallicRoughness

                        # Base color texture
                        if hasattr(pbr, 'baseColorTexture') and pbr.baseColorTexture is not None:
                            if hasattr(pbr.baseColorTexture, 'index'):
                                texture_idx = pbr.baseColorTexture.index
                                material_to_textures[material_idx].add(texture_idx)
                                print(f"Material {material_idx} uses texture {texture_idx} for baseColor")

                    # Other texture types (normal, emissive, etc.)
                    for texture_type in ['normalTexture', 'emissiveTexture', 'occlusionTexture']:
                        if hasattr(material, texture_type) and getattr(material, texture_type) is not None:
                            texture_ref = getattr(material, texture_type)
                            if hasattr(texture_ref, 'index'):
                                texture_idx = texture_ref.index
                                material_to_textures[material_idx].add(texture_idx)
                                print(f"Material {material_idx} uses texture {texture_idx} for {texture_type}")

            # Process external image files first
            if hasattr(gltf, 'images') and gltf.images:
                for image_idx, image in enumerate(gltf.images):
                    # Skip data URIs for now
                    if hasattr(image, 'uri') and image.uri and not image.uri.startswith('data:'):
                        decoded_uri = urllib.parse.unquote(image.uri)
                        image_path = os.path.join(model_dir, decoded_uri)

                        if os.path.exists(image_path):
                            print(f"Loading external texture: {image_path}")
                            texture_id = self.load_texture(image_path)
                            if texture_id:
                                self.texture_ids[image_idx] = texture_id
                                print(f"Loaded external texture {image_idx} with OpenGL ID {texture_id}")

            # Handle embedded images in GLB
            if is_glb and hasattr(gltf, 'images') and gltf.images:
                binary_blob = gltf.binary_blob()
                if binary_blob is not None:
                    for image_idx, image in enumerate(gltf.images):
                        # Skip images we've already handled
                        if image_idx in self.texture_ids:
                            continue
                        
                        # Handle embedded image in GLB
                        if hasattr(image, 'bufferView') and image.bufferView is not None:
                            buffer_view = gltf.bufferViews[image.bufferView]
                            buffer_offset = buffer_view.byteOffset or 0
                            buffer_length = buffer_view.byteLength

                            # Extract the image data
                            image_data = binary_blob[buffer_offset:buffer_offset + buffer_length]

                            if image_data:
                                # Get mime type
                                mime_type = 'image/png'  # Default
                                if hasattr(image, 'mimeType') and image.mimeType:
                                    mime_type = image.mimeType

                                # Create a PIL Image from the binary data
                                try:
                                    img = Image.open(io.BytesIO(image_data))
                                    print(f"Successfully loaded embedded image {image_idx} from buffer view {image.bufferView}")

                                    # Create OpenGL texture
                                    texture_id = self.create_texture_from_image(img)
                                    if texture_id:
                                        self.texture_ids[image_idx] = texture_id
                                        print(f"Created texture {image_idx} with OpenGL ID {texture_id} from embedded image")
                                except Exception as e:
                                    print(f"Failed to load embedded image {image_idx}: {e}")

            # Map texture images to materials for rendering
            for material_idx, texture_indices in material_to_textures.items():
                for texture_idx in texture_indices:
                    if texture_idx in texture_to_image:
                        image_idx = texture_to_image[texture_idx]
                        if image_idx in self.texture_ids:
                            # If we have multiple textures for a material, prioritize baseColor
                            # (This is a simplification - a proper PBR renderer would use all textures)
                            print(f"Material {material_idx} will use image {image_idx} with texture ID {self.texture_ids[image_idx]}")

            print(f"Texture loading completed. Loaded {len(self.texture_ids)} textures.")
        except Exception as e:
            import traceback
            print(f"Error in load_gltf_textures: {e}")
            print(traceback.format_exc())

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
    
    def scale_model(self):
        """Scale all meshes to fit the view using VBO data."""
        if not self.meshes or not self.vertex_vbos:
            print("No meshes or vertex VBOs to scale")
            return

        # Collect all vertex data from VBOs
        all_vertices = []
        for part_id in range(len(self.meshes)):
            if part_id in self.vertex_vbos and self.vertex_vbos[part_id] is not None:
                vbo = self.vertex_vbos[part_id]
                vbo.bind()
                # Get the data from the VBO (assuming float32, 3 components per vertex)
                vertex_data = np.frombuffer(
                    vbo.data, dtype=np.float32
                ).reshape(-1, 3)
                vbo.unbind()
                all_vertices.append(vertex_data)

        if not all_vertices:
            print("No vertex data found in VBOs")
            return

        # Stack all vertices to compute bounds
        all_vertices = np.vstack(all_vertices)
        min_bounds = np.min(all_vertices, axis=0)
        max_bounds = np.max(all_vertices, axis=0)
        bounds = np.vstack((min_bounds, max_bounds))

        size_range = bounds[1] - bounds[0]
        if np.max(size_range) == 0:
            print("Model has zero size range, skipping scaling")
            return

        # Use a scale factor to fit the view (adjust as needed)
        scale = 4.0 / max(size_range)

        # Calculate the centroid of all vertices
        centroid = np.mean(all_vertices, axis=0)

        # Scale and center each part’s vertex data
        for part_id in range(len(self.meshes)):
            if part_id in self.vertex_vbos and self.vertex_vbos[part_id] is not None:
                vbo = self.vertex_vbos[part_id]
                vbo.bind()
                # Get current vertex data
                vertices = np.frombuffer(
                    vbo.data, dtype=np.float32
                ).reshape(-1, 3)

                # Apply scaling and centering
                vertices *= scale
                vertices -= centroid * scale

                # Update the VBO with new data
                new_data = vertices.astype(np.float32).tobytes()
                glBufferData(GL_ARRAY_BUFFER, len(new_data), new_data, GL_STATIC_DRAW)
                vbo.unbind()
                print(f"Scaled and updated VBO for part {part_id}: {len(vertices)} vertices")

        self.update()

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
        return QSize(300, 300)
        
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