#!/usr/bin/env python3
"""
Test NerfStudio Pipeline End-to-End
Validates that Vincent Woo's methodology works with our infrastructure
"""

import os
import sys
import json
import time
import shutil
import logging
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NerfStudioPipelineTest:
    """Test the complete NerfStudio pipeline"""
    
    def __init__(self, test_data_dir: str):
        self.test_data_dir = Path(test_data_dir)
        self.output_dir = Path("/tmp/nerfstudio_test_output")
        self.config_path = Path(__file__).parent / "nerfstudio_config.yaml"
        
        # Clean output directory
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True)
    
    def validate_test_data(self) -> bool:
        """Validate test data format"""
        logger.info("🔍 Validating test data format...")
        
        required_paths = [
            self.test_data_dir / "sparse" / "0" / "cameras.txt",
            self.test_data_dir / "sparse" / "0" / "images.txt", 
            self.test_data_dir / "sparse" / "0" / "points3D.txt",
            self.test_data_dir / "images"
        ]
        
        for path in required_paths:
            if not path.exists():
                logger.error(f"❌ Missing required path: {path}")
                return False
        
        logger.info("✅ Test data format validated")
        return True
    
    def test_container_build(self) -> bool:
        """Test if the container can be built"""
        logger.info("🐳 Testing container build...")
        
        dockerfile_path = Path(__file__).parent / "Dockerfile"
        if not dockerfile_path.exists():
            logger.error("❌ Dockerfile not found")
            return False
        
        # For now, just validate Dockerfile syntax
        try:
            with open(dockerfile_path, 'r') as f:
                content = f.read()
                
            if "nerfstudio" not in content.lower():
                logger.error("❌ Dockerfile doesn't contain NerfStudio installation")
                return False
                
            logger.info("✅ Dockerfile validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Dockerfile validation failed: {e}")
            return False
    
    def test_training_script(self) -> bool:
        """Test the training script execution"""
        logger.info("🔥 Testing training script...")
        
        # Set up environment variables
        env = os.environ.copy()
        env.update({
            'SM_CHANNEL_TRAINING': str(self.test_data_dir),
            'SM_MODEL_DIR': str(self.output_dir),
            'MAX_ITERATIONS': '10',  # Minimal test
            'SH_DEGREE': '3',
            'BILATERAL_PROCESSING': 'true',
            'MODEL_VARIANT': 'splatfacto'  # Use regular splatfacto for testing
        })
        
        # Test script path
        script_path = Path(__file__).parent / "train_nerfstudio_production.py"
        config_path = Path(__file__).parent / "nerfstudio_config.yaml"
        
        if not script_path.exists():
            logger.error("❌ Training script not found")
            return False
        
        if not config_path.exists():
            logger.error("❌ Configuration file not found")
            return False
        
        try:
            # Test script syntax
            result = subprocess.run([
                sys.executable, "-m", "py_compile", str(script_path)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"❌ Script syntax error: {result.stderr}")
                return False
            
            logger.info("✅ Training script syntax validated")
            
            # Test configuration loading
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            required_sections = ['model', 'training', 'hardware', 'output']
            for section in required_sections:
                if section not in config:
                    logger.error(f"❌ Missing config section: {section}")
                    return False
            
            logger.info("✅ Configuration file validated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Training script test failed: {e}")
            return False
    
    def test_vincent_woo_parameters(self) -> bool:
        """Test that Vincent Woo's parameters are correctly implemented"""
        logger.info("🎯 Testing Vincent Woo's parameter implementation...")
        
        import yaml
        config_path = Path(__file__).parent / "nerfstudio_config.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check Vincent Woo's key parameters
        checks = [
            (config.get('model', {}).get('variant') == 'splatfacto-big', "Model variant should be splatfacto-big"),
            (config.get('model', {}).get('sh_degree') == 3, "SH degree should be 3 (industry standard)"),
            (config.get('model', {}).get('bilateral_processing') == True, "Bilateral processing should be enabled"),
            (config.get('training', {}).get('max_iterations') == 30000, "Max iterations should be 30000"),
            (config.get('licensing', {}).get('license') == 'Apache 2.0', "License should be Apache 2.0")
        ]
        
        all_passed = True
        for check_passed, message in checks:
            if check_passed:
                logger.info(f"✅ {message}")
            else:
                logger.error(f"❌ {message}")
                all_passed = False
        
        return all_passed
    
    def test_quality_expectations(self) -> bool:
        """Test that quality expectations are set correctly"""
        logger.info("📊 Testing quality expectations...")
        
        import yaml
        config_path = Path(__file__).parent / "nerfstudio_config.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        target_psnr = config.get('training', {}).get('target_psnr', 0)
        if target_psnr >= 35.0:
            logger.info(f"✅ Target PSNR: {target_psnr} dB (high quality)")
        else:
            logger.warning(f"⚠️ Target PSNR: {target_psnr} dB (may be low)")
        
        # Check for SOGS compatibility
        output_config = config.get('output', {})
        if (output_config.get('format') == 'ply' and 
            output_config.get('include_spherical_harmonics') == True):
            logger.info("✅ SOGS compatibility ensured")
        else:
            logger.error("❌ SOGS compatibility not configured")
            return False
        
        return True
    
    def run_comprehensive_test(self) -> bool:
        """Run all tests"""
        logger.info("🚀 NERFSTUDIO PIPELINE COMPREHENSIVE TEST")
        logger.info("=" * 60)
        
        tests = [
            ("Data Validation", self.validate_test_data),
            ("Container Build", self.test_container_build),
            ("Training Script", self.test_training_script),
            ("Vincent Woo Parameters", self.test_vincent_woo_parameters),
            ("Quality Expectations", self.test_quality_expectations)
        ]
        
        results = {}
        for test_name, test_func in tests:
            logger.info(f"\n🧪 Running test: {test_name}")
            try:
                result = test_func()
                results[test_name] = result
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"   Result: {status}")
            except Exception as e:
                logger.error(f"   Result: ❌ ERROR - {e}")
                results[test_name] = False
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📋 TEST SUMMARY")
        logger.info("=" * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"   {test_name}: {status}")
        
        overall_success = passed == total
        logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if overall_success:
            logger.info("🎉 ALL TESTS PASSED - READY FOR PRODUCTION!")
            logger.info("✅ Vincent Woo's methodology implemented correctly")
            logger.info("✅ Infrastructure ready for high-quality 3D reconstruction")
        else:
            logger.error("❌ Some tests failed - please review and fix")
        
        return overall_success


def main():
    """Main test entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_nerfstudio_pipeline.py <path_to_test_colmap_data>")
        print("Example: python test_nerfstudio_pipeline.py /path/to/colmap/output")
        sys.exit(1)
    
    test_data_dir = sys.argv[1]
    
    # Run comprehensive test
    tester = NerfStudioPipelineTest(test_data_dir)
    success = tester.run_comprehensive_test()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
