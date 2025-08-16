import torch
import torch.nn as nn
import numpy as np

class GaussianModel(nn.Module):
    """3D Gaussian Splatting Model."""
    
    def __init__(self, positions, colors, opacities):
        super().__init__()
        
        # Convert inputs to tensors if they aren't already
        if not isinstance(positions, torch.Tensor):
            positions = torch.tensor(positions, dtype=torch.float32)
        if not isinstance(colors, torch.Tensor):
            colors = torch.tensor(colors, dtype=torch.float32)
        if not isinstance(opacities, torch.Tensor):
            opacities = torch.tensor(opacities, dtype=torch.float32)
            
        # Initialize parameters
        self.positions = nn.Parameter(positions)
        self.colors = nn.Parameter(colors)
        self.opacities = nn.Parameter(opacities)
        
        # Initialize scales and rotations
        num_points = positions.shape[0]
        self.scales = nn.Parameter(torch.ones(num_points, 3) * 0.01)
        self.rotations = nn.Parameter(torch.zeros(num_points, 4))
        self.rotations.data[:, 0] = 1.0  # Identity quaternion
    
    @property
    def num_points(self):
        return self.positions.shape[0]
    
    def get_params(self):
        """Get all learnable parameters for optimizer."""
        return [self.positions, self.colors, self.opacities, self.scales, self.rotations]
    
    def render(self, camera):
        """Render the scene from a given camera viewpoint."""
        # This is a simplified render function
        # In a real implementation, this would use gsplat rasterization
        batch_size = 1
        height, width = 256, 256
        channels = 3
        
        # Create a dummy rendered image for now
        rendered = torch.rand(batch_size, channels, height, width, device=self.positions.device)
        
        return rendered, None
    
    def save_ply(self, path):
        """Save the model to a PLY file."""
        positions = self.positions.detach().cpu().numpy()
        colors = self.colors.detach().cpu().numpy()
        opacities = self.opacities.detach().cpu().numpy()
        scales = self.scales.detach().cpu().numpy()
        rotations = self.rotations.detach().cpu().numpy()
        
        num_points = positions.shape[0]
        
        with open(path, 'w') as f:
            f.write(f"""ply
format ascii 1.0
comment 3D Gaussian Splatting Model
element vertex {num_points}
property float x
property float y
property float z
property float opacity
property float scale_0
property float scale_1
property float scale_2
property float rot_0
property float rot_1
property float rot_2
property float rot_3
property uchar red
property uchar green
property uchar blue
end_header
""")
            
            for i in range(num_points):
                pos = positions[i]
                col = colors[i]
                opacity = opacities[i, 0] if opacities.ndim > 1 else opacities[i]
                scale = scales[i]
                rot = rotations[i]
                
                # Convert colors to 0-255 range
                r, g, b = int(col[0] * 255), int(col[1] * 255), int(col[2] * 255)
                
                f.write(f"{pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f} {opacity:.6f} "
                       f"{scale[0]:.6f} {scale[1]:.6f} {scale[2]:.6f} "
                       f"{rot[0]:.6f} {rot[1]:.6f} {rot[2]:.6f} {rot[3]:.6f} "
                       f"{r} {g} {b}\n") 