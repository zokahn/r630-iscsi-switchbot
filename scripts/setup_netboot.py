#!/usr/bin/env python3
# setup_netboot.py - Configure netboot support for OpenShift multiboot

import argparse
import os
import subprocess
import requests
import sys
import tempfile
import shutil

def setup_netboot_menu(truenas_ip, output_dir):
    """Create the netboot.xyz custom menu file"""
    # Create the custom menu content based on current netboot.xyz practices
    menu_content = """#!ipxe
###
### OpenShift Multiboot Menu
### Based on netboot.xyz menu format for consistency
###

# Set a custom title
set site_name OpenShift Installer
set os_name Red Hat OpenShift
set oc_version_menu 1

# Define our TrueNAS server IP
set tns_ip {truenas_ip}

######################
# Main Menu
######################
:openshift_menu
menu ${{site_name}} - ${{os_name}} Versions
item --gap -- --------------------------------
item --gap -- Available OpenShift Versions:
item 4.18 ${{os_name}} 4.18 Installation
item 4.17 ${{os_name}} 4.17 Installation 
item 4.16 ${{os_name}} 4.16 Installation
item --gap
item back Back to Main Menu...
item exit Exit to iPXE shell
choose version || goto openshift_exit
goto openshift_boot_${{version}}

######################
# OpenShift 4.18
######################
:openshift_boot_4.18
menu ${{os_name}} 4.18 Installation
item --gap -- ${{os_name}} 4.18 Boot Options
item normal Normal Installation
item --gap
item back Back to Version Selection...
choose boottype || goto openshift_menu
echo Selected ${{os_name}} 4.18 ${{boottype}} boot...
set url http://${{tns_ip}}/openshift_isos/4.18
goto openshift_boot_common

######################
# OpenShift 4.17
######################
:openshift_boot_4.17
menu ${{os_name}} 4.17 Installation
item --gap -- ${{os_name}} 4.17 Boot Options
item normal Normal Installation
item --gap
item back Back to Version Selection...
choose boottype || goto openshift_menu
echo Selected ${{os_name}} 4.17 ${{boottype}} boot...
set url http://${{tns_ip}}/openshift_isos/4.17
goto openshift_boot_common

######################
# OpenShift 4.16
######################
:openshift_boot_4.16
menu ${{os_name}} 4.16 Installation
item --gap -- ${{os_name}} 4.16 Boot Options
item normal Normal Installation
item --gap
item back Back to Version Selection...
choose boottype || goto openshift_menu
echo Selected ${{os_name}} 4.16 ${{boottype}} boot...
set url http://${{tns_ip}}/openshift_isos/4.16
goto openshift_boot_common

######################
# Common Boot Process
######################
:openshift_boot_common
imgfree
# We're using a simpler boot method here since the OpenShift ISOs 
# are already set up for Agent-based installation
kernel ${{url}}/agent.x86_64.iso || goto openshift_menu
boot || goto openshift_menu

######################
# Navigation
######################
:back
echo Returning to main menu...
sleep 1
chain https://netboot.omnisack.nl/ipxe/menu.ipxe

:openshift_exit
clear menu
exit
""".format(truenas_ip=truenas_ip)

    # Write the menu to a file
    menu_file = os.path.join(output_dir, "openshift.ipxe")
    with open(menu_file, "w") as f:
        f.write(menu_content)
    
    # Return the path to the generated menu file
    return menu_file

def verify_netboot():
    """Verify that netboot service is accessible"""
    try:
        # The main site should be accessible
        main_response = requests.head("https://netboot.omnisack.nl/", timeout=5)
        
        # We also need to check if custom menu endpoints are supported
        # This URL might need to be adjusted based on the actual server configuration
        menu_url = "https://netboot.omnisack.nl/custom/"
        menu_response = requests.head(menu_url, timeout=5)
        
        if main_response.status_code == 200:
            print("✅ netboot.omnisack.nl is accessible")
            if menu_response.status_code < 400:
                print("✅ Custom menu endpoints appear to be available")
                return True
            else:
                print(f"⚠️ Custom menu endpoint returned status code {menu_response.status_code}")
                print("⚠️ Will proceed but custom menu integration might not work")
                return True
        else:
            print(f"❌ netboot service returned status code {main_response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing netboot service: {e}")
        return False

def upload_to_truenas(local_file, truenas_ip, username, remote_path):
    """Upload a file to TrueNAS using SCP"""
    try:
        # Make sure the directory exists
        directory = os.path.dirname(remote_path)
        subprocess.run(["ssh", f"{username}@{truenas_ip}", f"mkdir -p {directory}"], check=True)
        
        # Upload the file
        subprocess.run(["scp", local_file, f"{username}@{truenas_ip}:{remote_path}"], check=True)
        print(f"✅ Uploaded {local_file} to {truenas_ip}:{remote_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error uploading file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Set up netboot support for OpenShift multiboot")
    parser.add_argument("--truenas-ip", default="192.168.2.245", help="TrueNAS IP address")
    parser.add_argument("--output-dir", help="Output directory for temporary files")
    parser.add_argument("--username", default="root", help="Username for TrueNAS SSH/SCP access")
    parser.add_argument("--menu-path", default="/mnt/test/netboot/openshift.ipxe", 
                      help="Path on TrueNAS where to store the menu file")
    parser.add_argument("--dry-run", action="store_true", 
                      help="Generate menu file without uploading to TrueNAS")
    parser.add_argument("--skip-verification", action="store_true",
                      help="Skip netboot service verification")
    
    args = parser.parse_args()
    
    # Use provided output directory or create a temporary one
    if args.output_dir:
        output_dir = args.output_dir
        os.makedirs(output_dir, exist_ok=True)
        should_cleanup = False
    else:
        output_dir = tempfile.mkdtemp()
        should_cleanup = True
    
    try:
        # Verify netboot is accessible (unless skipped)
        if not args.skip_verification and not verify_netboot():
            print("⚠️ netboot service is not accessible. Custom menu may not work.")
        
        # Create the iPXE menu
        menu_file = setup_netboot_menu(args.truenas_ip, output_dir)
        print(f"✅ Created iPXE menu at {menu_file}")
        
        # Upload to TrueNAS (unless in dry-run mode)
        if not args.dry_run:
            upload_success = upload_to_truenas(menu_file, args.truenas_ip, args.username, args.menu_path)
            if upload_success:
                print(f"✅ Uploaded menu to TrueNAS at {args.menu_path}")
            else:
                print(f"❌ Failed to upload menu to TrueNAS")
                return 1
        else:
            print("🔍 Dry run mode - menu file created but not uploaded to TrueNAS")
            print(f"📝 Menu content preview:")
            try:
                with open(menu_file, 'r') as f:
                    lines = f.readlines()
                    # Print header lines
                    print("   === Header ===")
                    for i in range(min(10, len(lines))):
                        print(f"   {lines[i].rstrip()}")
                    
                    # Print middle section with OpenShift 4.18 menu
                    if len(lines) > 30:
                        print("\n   === OpenShift 4.18 Menu Section ===")
                        start_line = 0
                        for i, line in enumerate(lines):
                            if ":openshift_boot_4.18" in line:
                                start_line = i
                                break
                        for i in range(start_line, min(start_line + 10, len(lines))):
                            print(f"   {lines[i].rstrip()}")
                    
                    # Print last few lines
                    if len(lines) > 10:
                        print("\n   === Footer ===")
                        for i in range(max(0, len(lines) - 5), len(lines)):
                            print(f"   {lines[i].rstrip()}")
            except Exception as e:
                print(f"   Error previewing file: {e}")
        
        print("\n📋 Netboot setup completed.")
        print("To use netboot, run:")
        print(f"./scripts/switch_openshift.py --server SERVER_IP --method netboot --netboot-menu openshift --reboot")
        
        return 0
    finally:
        # Clean up temporary directory if we created one
        if should_cleanup:
            print(f"Cleaning up temporary directory: {output_dir}")
            shutil.rmtree(output_dir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
