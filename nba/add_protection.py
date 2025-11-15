#!/usr/bin/env python3
"""
Add access protection to your HTML dashboard files
This inserts JavaScript at the top to check for valid access
"""

def add_access_protection(html_file):
    """Add access gate check to HTML file"""
    
    protection_script = """
<!-- ACCESS PROTECTION - Added automatically -->
<script>
(function() {
    // Check if user has valid access
    const hasAccess = sessionStorage.getItem('hasAccess');
    const accessCode = sessionStorage.getItem('accessCode');
    
    if (!hasAccess || !accessCode) {
        // No access - redirect to gate
        window.location.href = 'access_gate.html';
        return;
    }
    
    // Optional: Add watermark showing access type
    window.addEventListener('DOMContentLoaded', function() {
        const accessType = sessionStorage.getItem('accessType');
        
        if (accessType === 'trial') {
            const banner = document.createElement('div');
            banner.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: #fbbf24;
                color: black;
                padding: 0.5rem;
                text-align: center;
                font-weight: bold;
                z-index: 9999;
            `;
            banner.textContent = '🎁 Trial Access - Upgrade for full features';
            document.body.insertBefore(banner, document.body.firstChild);
        }
    });
})();
</script>
<!-- END ACCESS PROTECTION -->

"""
    
    # Read the HTML file
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if protection already exists
    if 'ACCESS PROTECTION' in content:
        print(f"⚠️  {html_file} already has protection - skipping")
        return False
    
    # Insert protection after <head> tag
    if '<head>' in content:
        content = content.replace('<head>', f'<head>\n{protection_script}', 1)
    else:
        print(f"❌ No <head> tag found in {html_file}")
        return False
    
    # Write back
    with open(html_file + '.protected', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Created protected version: {html_file}.protected")
    print(f"   To use: mv {html_file}.protected {html_file}")
    return True

if __name__ == '__main__':
    import sys
    
    print("🔒 HTML DASHBOARD PROTECTION TOOL")
    print("=" * 50)
    print()
    
    files_to_protect = [
        'nba_tracking_dashboard.html',
        'nba_model_output.html'
    ]
    
    for file in files_to_protect:
        try:
            add_access_protection(file)
        except FileNotFoundError:
            print(f"⚠️  {file} not found - skipping")
        except Exception as e:
            print(f"❌ Error processing {file}: {e}")
        print()
    
    print("=" * 50)
    print("✅ PROTECTION COMPLETE")
    print()
    print("📋 Next steps:")
    print("1. Review the .protected files")
    print("2. If they look good, replace originals:")
    print("   mv nba_tracking_dashboard.html.protected nba_tracking_dashboard.html")
    print("   mv nba_model_output.html.protected nba_model_output.html")
    print("3. Upload access_gate.html to your site")
    print("4. Users must enter code at access_gate.html first")
    print()
