import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def add_p_border_bottom(p, color="222222", sz="6", space="1"):
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), sz) # 6 = 3/4 pt, 8 = 1 pt
    bottom.set(qn('w:space'), space)
    bottom.set(qn('w:color'), color)
    pBdr.append(bottom)
    pPr.append(pBdr)

def add_hyperlink(paragraph, url, text, color="004B87", underline=False):
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    if color:
        c = OxmlElement('w:color')
        c.set(qn('w:val'), color)
        rPr.append(c)
    if underline:
        u = OxmlElement('w:u')
        u.set(qn('w:val'), 'single')
        rPr.append(u)
    new_run.append(rPr)
    text_elem = OxmlElement('w:t')
    text_elem.text = text
    new_run.append(text_elem)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink

def create_resume_docx(output_path="resume_master.docx"):
    doc = docx.Document()
    
    # Page Setup: Letter, 0.5 in margins
    for section in doc.sections:
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)
        section.top_margin = Inches(0.45)
        section.bottom_margin = Inches(0.45)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
    
    # Style Setup
    normal_style = doc.styles['Normal']
    font = normal_style.font
    font.name = 'Calibri'
    font.size = Pt(9.5)
    font.color.rgb = RGBColor(0x11, 0x11, 0x11)
    
    # Helper for adding section headers
    def add_section(title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title.upper())
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x11, 0x11, 0x11)
        add_p_border_bottom(p, color="333333", sz="8", space="2")
        return p

    # Helper for two-part heading line (left text, right text)
    def add_heading_line(left_bold_text, right_text, italic=False, space_before=2, space_after=0):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(7.5), WD_TAB_ALIGNMENT.RIGHT)
        p.paragraph_format.keep_with_next = True
        
        run_l = p.add_run(left_bold_text)
        if italic:
            run_l.italic = True
        else:
            run_l.bold = True
        run_l.font.size = Pt(9.5)
            
        p.add_run("\t")
        
        run_r = p.add_run(right_text)
        if italic:
            run_r.italic = True
        run_r.font.size = Pt(9.5)
        return p

    # Helper for bullet points
    def add_bullet(runs_data, space_after=1.5):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.08
        
        for text, bold, italic, code in runs_data:
            run = p.add_run(text)
            if bold:
                run.bold = True
            if italic:
                run.italic = True
            if code:
                run.font.name = 'Consolas'
                run.font.size = Pt(9)
            else:
                run.font.name = 'Calibri'
                run.font.size = Pt(9.5)
        return p

    # --- HEADER ---
    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_name.paragraph_format.space_before = Pt(0)
    p_name.paragraph_format.space_after = Pt(2)
    run_name = p_name.add_run("Golden Stickwood")
    run_name.bold = True
    run_name.font.size = Pt(18)
    run_name.font.color.rgb = RGBColor(0x11, 0x11, 0x11)
    
    p_contact1 = doc.add_paragraph()
    p_contact1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_contact1.paragraph_format.space_before = Pt(0)
    p_contact1.paragraph_format.space_after = Pt(1)
    r1 = p_contact1.add_run("Newmarket, ON (GTA)  |  Canadian Citizen  |  +1 (647) 649-8083  |  ")
    r1.font.size = Pt(9.5)
    add_hyperlink(p_contact1, "mailto:stickwood_jr@hotmail.com", "stickwood_jr@hotmail.com", color="004B87", underline=False)
    
    p_contact2 = doc.add_paragraph()
    p_contact2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_contact2.paragraph_format.space_before = Pt(0)
    p_contact2.paragraph_format.space_after = Pt(4)
    add_hyperlink(p_contact2, "https://www.linkedin.com/in/golden-q-stickwood-8404aa23b", "linkedin.com/in/golden-q-stickwood-8404aa23b", color="004B87", underline=False)
    r_sep = p_contact2.add_run("  |  ")
    r_sep.font.size = Pt(9.5)
    add_hyperlink(p_contact2, "https://github.com/StickwoodJr", "github.com/StickwoodJr", color="004B87", underline=False)

    # --- EDUCATION ---
    add_section("Education")
    add_heading_line("Seneca Polytechnic", "Toronto, ON", italic=False, space_before=2, space_after=0)
    add_heading_line("Ontario College Advanced Diploma in Computer Systems Technology (CTY) - Co-op Option", "Jan. 2026 - Present", italic=True, space_before=0, space_after=1)
    
    add_bullet([
        ("Academic Standing: ", True, False, False),
        ("4.0 / 4.0 GPA  |  President's Honour List (Completed Semesters 1 & 2, Expected Grad: 2028)", False, False, False)
    ])
    add_bullet([
        ("Relevant Coursework: ", True, False, False),
        ("Linux Server Admin (", False, False, False),
        ("OPS145, OPS245", False, False, True),
        ("), Cisco Networks & Routing (", False, False, False),
        ("CSN115, CSN205", False, False, True),
        ("), Windows Server Admin & Active Directory (", False, False, False),
        ("MST100, MST200", False, False, True),
        ("), System Security (", False, False, False),
        ("SEC220", False, False, True),
        ("), Strategic Problem Solving (", False, False, False),
        ("SPS120", False, False, True),
        (").", False, False, False)
    ], space_after=3)

    # --- TECHNICAL SKILLS ---
    add_section("Technical Skills")
    
    p_skill1 = doc.add_paragraph()
    p_skill1.paragraph_format.left_indent = Inches(0.1)
    p_skill1.paragraph_format.space_before = Pt(2)
    p_skill1.paragraph_format.space_after = Pt(1.5)
    p_skill1.paragraph_format.line_spacing = 1.08
    r = p_skill1.add_run("Systems & Virtualization: ")
    r.bold = True
    p_skill1.add_run("Linux (Debian headless, Ubuntu Server, RHEL/Rocky), Windows Server 2019/2022, Windows 10/11, KVM/QEMU, libvirt/virsh, Proxmox VE, VMware Workstation, Active Directory (AD DS), Group Policy (GPOs), Entra ID, systemd, LVM")

    p_skill2 = doc.add_paragraph()
    p_skill2.paragraph_format.left_indent = Inches(0.1)
    p_skill2.paragraph_format.space_before = Pt(0)
    p_skill2.paragraph_format.space_after = Pt(1.5)
    p_skill2.paragraph_format.line_spacing = 1.08
    r = p_skill2.add_run("Networking & Security: ")
    r.bold = True
    p_skill2.add_run("Cisco IOS/IOSv, Zone-Based Firewalls (ZFW), TCP/IP, Subnetting (VLSM/CIDR), VLAN / VLANs (802.1Q), NAT/PAT Overload, ACLs, Cloudflare Zero Trust Tunnels, Tailscale (WireGuard), nftables/iptables, Wireshark, Nmap")

    p_skill3 = doc.add_paragraph()
    p_skill3.paragraph_format.left_indent = Inches(0.1)
    p_skill3.paragraph_format.space_before = Pt(0)
    p_skill3.paragraph_format.space_after = Pt(3)
    p_skill3.paragraph_format.line_spacing = 1.08
    r = p_skill3.add_run("Scripting, Support & Tools: ")
    r.bold = True
    p_skill3.add_run("Bash shell scripting, Python 3, PowerShell, Docker, Git/GitHub, NGINX, Syslog/Journald log analysis, hardware diagnostics, Tier 1/2 troubleshooting, customer service")

    # --- TECHNICAL PROJECTS ---
    add_section("Technical Projects")
    
    p_proj = doc.add_paragraph()
    p_proj.paragraph_format.space_before = Pt(2)
    p_proj.paragraph_format.space_after = Pt(1)
    p_proj.paragraph_format.tab_stops.add_tab_stop(Inches(7.5), WD_TAB_ALIGNMENT.RIGHT)
    p_proj.paragraph_format.keep_with_next = True
    
    r_pt = p_proj.add_run("Multi-Zone Virtualized Infrastructure & Cisco Network Lab")
    r_pt.bold = True
    r_pt.font.size = Pt(9.5)
    p_proj.add_run("  |  ")
    add_hyperlink(p_proj, "https://github.com/StickwoodJr/Home-Lab", "github.com/StickwoodJr/Home-Lab", color="004B87", underline=False)
    p_proj.add_run("\t")
    r_pdate = p_proj.add_run("2025 - 2026")
    r_pdate.font.size = Pt(9.5)
    
    add_bullet([
        ("Architected a multi-zone virtualized homelab on headless Debian 13 (", False, False, False),
        ("labhost", False, False, True),
        ("), isolating WAN, DMZ (", False, False, False),
        ("192.168.50.0/24", False, False, True),
        ("), and LAN zones with least-privilege default-deny security.", False, False, False)
    ])
    add_bullet([
        ("Configured a virtualized 3-legged Cisco IOSv appliance running Zone-Based Policy Firewall (ZFW), dynamic NAT overload (PAT), and stateful inspection policies.", False, False, False)
    ])
    add_bullet([
        ("Deployed zero-trust outbound ingress and remote management via Cloudflare Tunnels and Tailscale (WireGuard mesh), eliminating public port forwarding and WAN exposure.", False, False, False)
    ])
    add_bullet([
        ("Engineered automated disaster recovery shell scripts (", False, False, False),
        ("virsh managedsave", False, False, True),
        (") safely quiescing running VMs and generating scheduled, compressed backups.", False, False, False)
    ])
    add_bullet([
        ("Authored production-grade engineering documentation including 5 Architectural Decision Records (ADRs) and 7 post-mortem incident response troubleshooting reports.", False, False, False)
    ], space_after=3)

    # --- PROFESSIONAL EXPERIENCE ---
    add_section("Professional Experience")
    
    # 1. Newmarket Pressure Washing
    add_heading_line("Newmarket Pressure Washing", "Newmarket, ON", italic=False, space_before=2, space_after=0)
    add_heading_line("Founder & Lead Operator", "May 2022 - Aug. 2025", italic=True, space_before=0, space_after=1)
    
    add_bullet([
        ("Founded and operated a commercial and residential exterior cleaning business, winning the competitive York Region Summer Company Entrepreneurship Grant.", False, False, False)
    ])
    add_bullet([
        ("Achieved profitability within the first month of operation, generating ", False, False, False),
        ("more than $10,000 in lifetime revenue", True, False, False),
        (" across dozens of commercial and residential clients with a 100% satisfaction rating.", False, False, False)
    ])
    add_bullet([
        ("Directed end-to-end business operations including client acquisition, technical service estimating, scheduling, invoicing, and high-retention customer service.", False, False, False)
    ])
    add_bullet([
        ("Performed routine hardware troubleshooting, preventative maintenance, and component repairs on commercial high-pressure pumping equipment.", False, False, False)
    ])
    add_bullet([
        ("Featured in regional publications by YorkRegion.com and NewmarketToday for youth entrepreneurship and business leadership.", False, False, False)
    ], space_after=3)

    # 2. Brookstone Windows & Doors
    add_heading_line("Brookstone Windows & Doors", "Aurora, ON", italic=False, space_before=2, space_after=0)
    add_heading_line("Sales & Technical Solutions Representative", "Oct. 2025 - Dec. 2025", italic=True, space_before=0, space_after=1)
    
    add_bullet([
        ("Conducted technical requirements discovery with residential property owners to consult on custom window and door specifications and energy efficiency ratings.", False, False, False)
    ])
    add_bullet([
        ("Analyzed structural specifications, resolved customer technical inquiries, and scheduled qualified technical consultations in a high-pace quota environment.", False, False, False)
    ], space_after=3)

    # 3. Newmarket Minor Hockey Association
    add_heading_line("Newmarket Minor Hockey Association (NMHA)", "Newmarket, ON", italic=False, space_before=2, space_after=0)
    add_heading_line("Ice Hockey Referee & Official", "Oct. 2020 - Mar. 2024", italic=True, space_before=0, space_after=1)
    
    add_bullet([
        ("Officiated 300+ competitive youth and adult league games over 4 seasons under Hockey Canada rules, making rapid, high-pressure decisions under close scrutiny.", False, False, False)
    ])
    add_bullet([
        ("De-escalated contentious on-ice disputes through clear, calm communication with coaches and team officials, ensuring player safety.", False, False, False)
    ], space_after=0)

    doc.save(output_path)
    print(f"Successfully created {output_path}")

if __name__ == "__main__":
    create_resume_docx()
