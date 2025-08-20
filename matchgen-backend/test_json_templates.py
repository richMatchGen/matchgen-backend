#!/usr/bin/env python3
"""
Test script for the new JSON-based template system.
This demonstrates how much simpler the new approach is.
"""

# Example template configurations
matchday_template = {
    "elements": {
        "date": {
            "type": "text",
            "position": {"x": 200, "y": 150},
            "style": {
                "fontSize": 24,
                "fontFamily": "Arial",
                "color": "#FFFFFF",
                "alignment": "center"
            }
        },
        "time": {
            "type": "text",
            "position": {"x": 400, "y": 150},
            "style": {
                "fontSize": 24,
                "fontFamily": "Arial",
                "color": "#FFFFFF",
                "alignment": "center"
            }
        },
        "venue": {
            "type": "text",
            "position": {"x": 300, "y": 250},
            "style": {
                "fontSize": 20,
                "fontFamily": "Arial",
                "color": "#FFFFFF",
                "alignment": "center"
            }
        }
    }
}

upcoming_fixture_template = {
    "elements": {
        "opponent": {
            "type": "text",
            "position": {"x": 300, "y": 200},
            "style": {
                "fontSize": 28,
                "fontFamily": "Arial",
                "color": "#FFFFFF",
                "alignment": "center",
                "fontWeight": "bold"
            }
        },
        "date": {
            "type": "text",
            "position": {"x": 300, "y": 250},
            "style": {
                "fontSize": 20,
                "fontFamily": "Arial",
                "color": "#FFFFFF",
                "alignment": "center"
            }
        },
        "time": {
            "type": "text",
            "position": {"x": 300, "y": 280},
            "style": {
                "fontSize": 18,
                "fontFamily": "Arial",
                "color": "#FFFFFF",
                "alignment": "center"
            }
        }
    }
}

def render_template(template_config, data):
    """
    Simulate rendering a template with the new JSON configuration.
    This is much simpler than the old database-based approach!
    """
    print(f"🎨 Rendering template with {len(template_config['elements'])} elements")
    
    for element_key, element_config in template_config['elements'].items():
        element_type = element_config['type']
        position = element_config['position']
        style = element_config['style']
        
        # Get the actual data for this element
        element_data = data.get(element_key, f"[{element_key}]")
        
        print(f"  📝 {element_key}: '{element_data}' at ({position['x']}, {position['y']})")
        print(f"     Style: {style['fontSize']}px {style['fontFamily']}, {style['color']}")
    
    print("✅ Template rendered successfully!")

def update_element_position(template_config, element_key, new_x, new_y):
    """
    Update an element's position - much simpler than database operations!
    """
    if element_key in template_config['elements']:
        template_config['elements'][element_key]['position']['x'] = new_x
        template_config['elements'][element_key]['position']['y'] = new_y
        print(f"📍 Updated {element_key} position to ({new_x}, {new_y})")
    else:
        print(f"❌ Element '{element_key}' not found")

def update_element_style(template_config, element_key, style_updates):
    """
    Update an element's style - no database queries needed!
    """
    if element_key in template_config['elements']:
        template_config['elements'][element_key]['style'].update(style_updates)
        print(f"🎨 Updated {element_key} style: {style_updates}")
    else:
        print(f"❌ Element '{element_key}' not found")

# Test the new system
if __name__ == "__main__":
    print("🚀 Testing New JSON-Based Template System")
    print("=" * 50)
    
    # Test 1: Render a matchday template
    print("\n1️⃣ Rendering Matchday Template:")
    matchday_data = {
        "date": "Saturday, 15th March",
        "time": "3:00 PM",
        "venue": "Home Stadium"
    }
    render_template(matchday_template, matchday_data)
    
    # Test 2: Update element position
    print("\n2️⃣ Updating Element Position:")
    update_element_position(matchday_template, "date", 250, 180)
    
    # Test 3: Update element style
    print("\n3️⃣ Updating Element Style:")
    update_element_style(matchday_template, "date", {
        "fontSize": 28,
        "color": "#FFD700",
        "fontWeight": "bold"
    })
    
    # Test 4: Render updated template
    print("\n4️⃣ Rendering Updated Template:")
    render_template(matchday_template, matchday_data)
    
    # Test 5: Render upcoming fixture template
    print("\n5️⃣ Rendering Upcoming Fixture Template:")
    fixture_data = {
        "opponent": "Manchester United",
        "date": "Next Saturday",
        "time": "7:30 PM"
    }
    render_template(upcoming_fixture_template, fixture_data)
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\n🎯 Benefits of the new system:")
    print("   • No complex database relationships")
    print("   • Easy to modify positions and styles")
    print("   • Simple JSON structure")
    print("   • No database queries for updates")
    print("   • Easy to version control")
    print("   • Much faster development")
