"""
Script to add defer() to ALL commands that don't have it
"""
import os
import re

def add_defer_to_command(content):
    """Add defer() to commands that don't have it"""
    
    # Pattern: find @app_commands.command followed by async def, then check if defer() exists
    pattern = r'(@app_commands\.command\([^\)]+\).*?)(async def \w+\([^)]+\).*?:)(.*?)(?=\n        await interaction\.response\.send_message|await interaction\.response\.defer|$)'
    
    def replacer(match):
        decorator = match.group(1)
        func_sig = match.group(2)
        func_body = match.group(3)
        
        # Check if already has defer
        if 'await interaction.response.defer' in func_body:
            return match.group(0)  # Already has defer, skip
            
        # Check if has immediate response
        if 'await interaction.response.send_message' in func_body:
            # Add defer before first actual logic
            lines = func_body.split('\n')
            new_lines = []
            added_defer = False
            
            for line in lines:
                if not added_defer and line.strip() and not line.strip().startswith('"""') and not line.strip().startswith('#'):
                    # Add defer before first real code line
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(' ' * indent + 'await interaction.response.defer()')
                    added_defer = True
                new_lines.append(line)
            
            if added_defer:
                new_func_body = '\n'.join(new_lines)
                # Replace send_message with followup.send
                new_func_body = new_func_body.replace(
                    'await interaction.response.send_message',
                    'await interaction.followup.send'
                )
                return decorator + func_sig + new_func_body
        
        return match.group(0)
    
    return re.sub(pattern, replacer, content, flags=re.DOTALL | re.MULTILINE)


def process_file(filepath):
    """Process a single Python file"""
    print(f"Processing: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple approach: find interaction.response.send_message and add defer before it
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a response.send_message without prior defer
        if 'await interaction.response.send_message' in line:
            # Look backwards to see if there's a defer
            has_defer = False
            for j in range(max(0, i-10), i):
                if 'await interaction.response.defer' in lines[j]:
                    has_defer = True
                    break
            
            if not has_defer:
                # Add defer before this line
                indent = len(line) - len(line.lstrip())
                new_lines.append(' ' * indent + 'await interaction.response.defer()')
                # Change send_message to followup.send
                line = line.replace('await interaction.response.send_message', 'await interaction.followup.send')
        
        new_lines.append(line)
        i += 1
    
    new_content = '\n'.join(new_lines)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✅ Updated {filepath}")
        return True
    else:
        print(f"  ⏭️  No changes needed")
        return False


def main():
    cogs_dir = os.path.join(os.path.dirname(__file__), 'cogs')
    
    updated_count = 0
    for filename in os.listdir(cogs_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            filepath = os.path.join(cogs_dir, filename)
            if process_file(filepath):
                updated_count += 1
    
    print(f"\n✅ Done! Updated {updated_count} files")


if __name__ == '__main__':
    main()
