---
framework_version: 1.2.6
---

# Candidate Profile

## Identity
- **Name:** Golden Stickwood
- **Location:** Newmarket, ON, Canada (Greater Toronto Area)
- **Phone:** +1 647-649-8083
- **Email:** stickwood_jr@hotmail.com
- **LinkedIn:** https://www.linkedin.com/in/golden-q-stickwood-8404aa23b/
- **GitHub:** https://github.com/StickwoodJr
- **Status:** 3rd-semester student enrolled in Seneca Polytechnic's Computer Systems Technology (CTY/CTYC) Co-op program; eligible for Winter 2027 co-op work term (Jan - Apr 2027). Canadian Citizen (authorized to work in Canada; no sponsorship required).
- **Driver's License & Mobility:** Valid Ontario G driver's license with access to a reliable vehicle. Able and willing to commute and travel across York Region and the GTA (Newmarket, Aurora, Markham, Vaughan, Woodbridge, Toronto).
- **Constraints:** Available for full-time 4-month co-op work term (Jan. 11, 2027 - Apr. 23, 2027); returning to studies upon completion.

### Languages
| Language | Level | Notes |
|----------|-------|-------|
| English | Native / C2 Fluent | Primary language of instruction and professional communication |

## Education

| Degree | Period | Institution | Key Topics & Standing |
|--------|--------|-------------|-----------------------|
| Ontario College Advanced Diploma in Computer Systems Technology (CTY) - Co-op Option | Jan. 2026 - Present (Expected Grad: 2028) | Seneca Polytechnic (Toronto, ON) | 4.0 / 4.0 GPA, President's Honour List. Focus on enterprise infrastructure, network engineering, systems administration, and security. |

### Completed Coursework & Academic Performance
- **Semester 1 (4.0 GPA):**
  - `SPS 120`: Strategic Problem Solving - A+
  - `OPS 145`: Introduction to Linux - A+
  - `MST 100`: Intro to Microsoft Services - A+
  - `CSN 115`: Intro to Computer and Network - A+
  - `COM 101`: Communicating Across Contexts - A+
- **Semester 2 (4.0 GPA):**
  - `SEC 220`: Intro to System Security - A+
  - `OPS 245`: Open Systems Server - A
  - `NAT 101`: Is There Life Beyond Earth? - A+
  - `MST 200`: Microsoft Server Admin - A+
  - `FLM 278`: Introduction to Film Studies - A+
  - `CSN 205`: Static Networks - A

### Key Coursework & Verified Competencies (Primary Evidence)
- **Active Directory & Identity Management (`MST100`, `MST200`):** Promoted Windows Server 2016 to Active Directory Domain Controller; structured Organizational Units (OUs); created Global and Domain Local Groups using AGDLP role-based access; automated batch user onboarding via custom PowerShell scripts (`bulk_users.ps1`) and `New-ADUser`; configured GPO security baselines, password policies, and account lockout policies.
- **Windows Systems & Remote Administration (`MST100`, `MST200`):** Configured Windows Server 2016 (Standard & Server Core) and Windows 10/11 Pro clients; remote troubleshooting using RSAT, Windows Admin Center (Port 6516), Server Manager multi-server console, and RDP.
- **Network Infrastructure Services (`MST200`):** Deployed Windows DHCP Server role; authorized DHCP in AD DS (`Add-DhcpServerInDC`); configured IP scopes, options, and static MAC reservations; integrated DHCP with Dynamic DNS (DDNS) forward lookup zones (`_msdcs` and host A records).
- **Print & File Server Administration (`MST200`):** Configured NTFS permissions, shared folder permissions, and mapped user home drives (`K:`); published shared resources into Active Directory; deployed network printers, printer drivers, TCP/IP ports, print queues, and printer pooling (`Add-Printer`, `Add-PrinterDriver`, `Add-PrinterPort`).
- **Cloud Infrastructure & Virtualization (`MST200`, `Home-Lab`):** Provisioned Windows Server 2019 Datacenter virtual machines in Microsoft Azure DevTest Labs; deployed AD DS on Azure VMs (`SenecaIDAZ1`), joined secondary Azure VMs (`SenecaIDAZ2`) to cloud domain, and managed via Azure portal and RDP. Virtualization experience with VMware Workstation Pro, Oracle VirtualBox, and Linux KVM/virsh hypervisors.
- **Network Engineering & Hardware Diagnostics (`CSN115`, `CSN205`):** PC hardware component diagnostics (motherboards, CPUs, RAM, storage, power supplies); IPv4 subnetting and Variable Length Subnet Masking (VLSM); configured static routes, default routes, single-area OSPFv2, and 802.1Q VLAN trunking on Cisco Catalyst switches and routers; network diagnostic CLI verification (`ping`, `ipconfig`, `tracert`, `nslookup`, `show ip route`).
- **PowerShell & Systems Automation (`MST100`, `MST200`):** Scripting in PowerShell 5.1 and ISE; implemented control flow, variables, file manipulation (`New-Item`, `Copy-Item`, `Remove-Item`), and service lifecycle management (`Get-Service`, `Start-Service`, `Stop-Service`, `Restart-Service`).
- **Linux Administration & Boundary Security (`OPS145`, `OPS245`, `SEC220`):** Installed Debian 12 bare-metal to bootable SSDs; user/group administration, package management (`apt`, `dpkg`), granular sudo privilege delegation (`/etc/sudoers.d/`); systemd service management (`systemctl`); network packet inspection with Wireshark and Nmap; local firewall auditing (`iptables`/`ufw`).

## Independent Technical Projects

### Multi-Zone Virtualized Infrastructure & Cisco Network Lab (2025 - 2026)
- **Repository:** https://github.com/StickwoodJr/Home-Lab
- Architected a 3-tier virtualized infrastructure on headless Debian 13 (`labhost`), isolating WAN, DMZ (`192.168.50.0/24`), and LAN zones with least-privilege default-deny security.
- Configured a virtualized 3-legged Cisco IOSv appliance running Zone-Based Policy Firewall (ZFW), dynamic NAT overload (PAT), and stateful packet inspection policies.
- Deployed zero-trust outbound ingress and remote management via Cloudflare Tunnels and Tailscale (WireGuard mesh), eliminating public port forwarding.
- Engineered automated disaster recovery shell scripts (`virsh managedsave`, `backupVMs.bash`, `restoreVM.bash`) safely quiescing running VMs and generating scheduled, compressed backups.
- Authored production-grade engineering documentation including 5 Architecture Decision Records (ADRs) and 7 incident response post-mortems.

## Professional Experience

### Founder & Lead Operator — Newmarket Pressure Washing (Newmarket, ON)
*May 2022 - Aug. 2025*
- Founded and operated an exterior surface cleaning business, winning the competitive York Region Summer Company Entrepreneurship Grant.
- Managed end-to-end customer service operations across phone and in-person channels: incident intake, technical problem diagnosis, scheduling, and invoicing, maintaining a 100% satisfaction rating.
- Performed routine hardware diagnostics, preventative maintenance, and mechanical/electrical troubleshooting on high-pressure pump systems to maximize uptime.
- Achieved profitability within first month of operation, generating over $20,000 in lifetime revenue across 100+ clients with high-retention repeat business.
- Featured in regional publications by YorkRegion.com and NewmarketToday for youth entrepreneurship and business leadership.

### Sales & Technical Solutions Representative — Brookstone Windows & Doors (Aurora, ON)
*Oct. 2025 - Dec. 2025*
- Conducted technical requirements discovery with property owners, translating complex engineering specifications and energy efficiency ratings clearly for non-technical clients.
- Analyzed structural specifications, resolved customer technical inquiries, and scheduled qualified technical consultations in a high-pace quota environment.

### Ice Hockey Referee & Official — Newmarket Minor Hockey Association (NMHA) (Newmarket, ON)
*Oct. 2020 - Mar. 2024*
- Officiated 60+ competitive youth and adult league games over 4 seasons under Hockey Canada rules, making rapid, high-pressure decisions under close scrutiny.
- De-escalated contentious on-ice disputes through clear, calm communication with coaches and team officials, ensuring player safety.

## Technical Skills Summary
- **IT Operations & Endpoint Support:** Windows 10/11 desktop troubleshooting, PC hardware/component diagnostics, peripherals, meeting room AV, network print queues (`Add-Printer`), remote management (RSAT, RDP, Windows Admin Center).
- **Directory Services & Infrastructure:** Active Directory Domain Services (AD DS), OUs, AGDLP group nesting, Group Policy Objects (GPOs), DHCP scopes & reservations, Dynamic DNS (DDNS), IPv4 subnetting/VLSM, Cisco Catalyst 802.1Q VLANs.
- **Cloud, Virtualization & Scripting:** Microsoft Azure portal (DevTest Labs VM deployment), VMware Workstation Pro, Linux KVM/virsh, PowerShell scripting (`bulk_users.ps1`, `New-ADUser`, `Get-Service`), Bash automation, SOP documentation, AI-assisted workflows with Claude Code.
- **Documentation & Methodologies:** Architecture Decision Records (ADRs), incident root-cause analysis, ticketing/dispatch workflow discipline, preventative maintenance schedules.
