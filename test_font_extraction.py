#!/usr/bin/env python3
"""
Test script to verify font extraction from PSD files.
This can be run to test the font extraction logic independently.
"""

import sys
import os
import logging

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_font_extraction(psd_file_path):
    """Test font extraction from a PSD file."""
    try:
        from psd_tools import PSDImage
        
        logger.info(f"Loading PSD file: {psd_file_path}")
        psd = PSDImage.open(psd_file_path)
        
        logger.info(f"PSD loaded successfully. Dimensions: {psd.width}x{psd.height}")
        
        text_layers = []
        for layer in psd.descendants():
            if layer.kind == 'type':  # Text layer
                text_layers.append(layer)
                logger.info(f"Found text layer: {layer.name}")
                
                # Test the extraction logic
                font_size = None
                font_family = None
                font_color = None
                font_weight = None
                
                # Try engine_dict method
                if hasattr(layer, 'engine_dict') and layer.engine_dict:
                    engine_dict = layer.engine_dict
                    logger.info(f"Engine dict available: {type(engine_dict)}")
                    logger.info(f"Engine dict keys: {list(engine_dict.keys()) if isinstance(engine_dict, dict) else 'Not a dict'}")
                    
                    try:
                        if 'StyleRun' in engine_dict and 'RunArray' in engine_dict['StyleRun']:
                            run_array = engine_dict['StyleRun']['RunArray']
                            if run_array and len(run_array) > 0:
                                style_sheet_data = run_array[0].get('StyleSheet', {}).get('StyleSheetData', {})
                                
                                if 'FontSize' in style_sheet_data:
                                    font_size = float(style_sheet_data['FontSize'])
                                    logger.info(f"✓ Extracted font size: {font_size}")
                                
                                if 'FontName' in style_sheet_data:
                                    font_family = str(style_sheet_data['FontName'])
                                    logger.info(f"✓ Extracted font family: {font_family}")
                                
                                if 'FontStyleName' in style_sheet_data:
                                    font_weight = str(style_sheet_data['FontStyleName'])
                                    logger.info(f"✓ Extracted font weight: {font_weight}")
                                
                                if 'FillColor' in style_sheet_data:
                                    fill_color = style_sheet_data['FillColor']
                                    if 'Values' in fill_color and fill_color['Values']:
                                        values = fill_color['Values']
                                        if len(values) >= 3:
                                            r = int(values[0] * 255) if values[0] is not None else 255
                                            g = int(values[1] * 255) if values[1] is not None else 255
                                            b = int(values[2] * 255) if values[2] is not None else 255
                                            font_color = f"#{r:02x}{g:02x}{b:02x}"
                                            logger.info(f"✓ Extracted font color: {font_color}")
                    except (KeyError, IndexError, TypeError) as e:
                        logger.warning(f"Could not parse engine_dict structure: {str(e)}")
                
                # Log results
                logger.info(f"Layer '{layer.name}' results:")
                logger.info(f"  Font Size: {font_size}")
                logger.info(f"  Font Family: {font_family}")
                logger.info(f"  Font Color: {font_color}")
                logger.info(f"  Font Weight: {font_weight}")
                logger.info(f"  Text Content: '{layer.text}'")
                logger.info(f"  Layer Size: {layer.width}x{layer.height}")
                logger.info("-" * 50)
        
        logger.info(f"Found {len(text_layers)} text layers total")
        return len(text_layers) > 0
        
    except Exception as e:
        logger.error(f"Error testing font extraction: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_font_extraction.py <path_to_psd_file>")
        sys.exit(1)
    
    psd_file = sys.argv[1]
    if not os.path.exists(psd_file):
        print(f"Error: PSD file '{psd_file}' not found")
        sys.exit(1)
    
    success = test_font_extraction(psd_file)
    if success:
        print("✓ Font extraction test completed successfully")
    else:
        print("✗ Font extraction test failed")
        sys.exit(1)
