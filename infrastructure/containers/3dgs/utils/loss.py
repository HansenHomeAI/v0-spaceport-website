import torch
import torch.nn.functional as F

class Loss:
    """Loss function for 3D Gaussian Splatting training."""
    
    def __init__(self):
        pass
    
    def __call__(self, rendered_image, gt_image):
        """Calculate loss and PSNR between rendered and ground truth images."""
        # L1 loss
        l1_loss = F.l1_loss(rendered_image, gt_image)
        
        # Calculate PSNR
        mse = F.mse_loss(rendered_image, gt_image)
        psnr = -10 * torch.log10(mse + 1e-8)
        
        return l1_loss, psnr.item() 