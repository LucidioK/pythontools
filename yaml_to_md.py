
# pip install pyyaml

import yaml
from yaml.loader import SafeLoader
import sys
import os


def yaml_to_md(yaml_file_path:str) -> str:
    def indented(l:list) -> list:
        return ("\n".join([f"> {item}" for item in l]) if l else "") + "\n"

    def bulleted(l:list) -> list:
        return ("\n".join([f"* {item}" for item in l]) if l else "") + "\n"

    with open(yaml_file_path) as f:
        data = yaml.load(f, Loader=SafeLoader)
    md_file_path = f"{os.path.splitext(yaml_file_path)[0]}.md"
    with open(md_file_path, mode='w') as f:
        f.write(f"# {data['name']}\n")
        f.write(f"\n**{data['phone']} {data['email']} {data['linkedIn']}**<br/><br/>\n")
        f.write(' '.join(data['description']))
        f.write('\n## Skills\n')
        f.write(indented(data['skills']))
        f.write(indented(data['programmingLanguages']))
        f.write('\n## Tech Stacks\n')
        for ts in data['techStacks']:
            ts = ts['techStack']
            f.write(f"\n### On {ts['cloud']}\n")
            f.write(indented(ts['stack']))
        f.write('\n## Professional Experience\n')    
        for pe in data['professionalExperiences']:
            pe = pe['professionalExperience']
            f.write(f"\n### {pe['title']} {pe['company']} {pe['startingMonth']} {pe['endingMonth']}\n")
            f.write(bulleted(pe['details']))
            f.write(bulleted(pe['links']))
        f.write('\n## Education\n')    
        for ed in [x['detail'] for x in data['education']]:
            f.write(f"{ed['degree']} - {ed['area']} - {ed['university']}<br/>\n")

if __name__ == "__main__":
    fn = sys.argv[1] if len(sys.argv) == 2 else r'C:\Users\lucid\OneDrive\LKPortfolio\cvlk3.yaml'
    yaml_to_md(fn)
