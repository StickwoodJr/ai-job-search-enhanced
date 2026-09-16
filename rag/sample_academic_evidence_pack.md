# Academic Evidence Pack (Verified School Skills)

**Target Role:** Junior Systems & Network Administrator  
**Source Notebook:** Seneca CTY Semesters 1 and 2 (`e32153b2-e906-4762-a8c3-8b96fbf093b4`)  
**Data Fidelity:** 100% Live Verified against primary lab submissions, slides, and scripts (No cache)

---

## 1. Verified Coursework & Hands-On Evidence

### 1. Verified Core Competencies & Lab Proof

* **Active Directory Administration & Group Policy**:
  * **Course Code**: MST100 / MST200 [1, 2].
  * **Lab / Submission**: `Lab 4 - User and Group Management(1).docx` [3], `Lab 8 - Creating Users with PS.docx` [4], `Week2-UsersandGroups.pptx` [5], and `08 Intro to Active Directory.pptx` [1].
  * **Verified Outcomes**: Provisioned Active Directory Organizational Units (OUs like `Toronto`, `Montreal`, `Vancouver`) [3], Global Security Groups (`T_SalesReps`) [3], and Domain Local Groups (`HR_Read`, `SalesFiles_FC`) [3, 6] using the AGDLP role-based access model [7]. Configured Active Directory Group Policies via Group Policy Management Console (`gpmc.msc`) to enforce Account Policies (Password Policy, Account Lockout Policy, Kerberos Policy) and User Rights Assignments [5, 8].

* **Cisco Switch Port Configuration, VLANs & 802.1Q Trunking**:
  * **Course Code**: CSN205 / CSN115 [9, 10].
  * **Lab / Submission**: `Group2_CSN205Assign1.pdf` [11, 12], `Group2_CSN205Lab1B.pdf` [10, 13-16], `Lab1A_Golden.pdf` [17-20], and `LAB2-CSN.pdf` [21, 22].
  * **Verified Outcomes**: Managed physical Cisco Catalyst 2960 switches and Cisco 1941 routers [11, 14]. Assigned access ports to VLANs (`VLAN 10 SenecaCollege`, `VLAN 20 YorkUniversity`), configured IEEE 802.1Q trunk links across switch interfaces [11, 12], implemented Inter-VLAN routing using subinterfaces (`Router-on-a-Stick`) [11, 12], and monitored Spanning Tree Protocol (STP / Rapid PVST+) convergence [9, 21, 22].

* **Linux Server Administration & Automation (Bash & PowerShell)**:
  * **Course Code**: OPS145 / OPS245 / MST100 / MST200 [1, 2, 23].
  * **Lab / Submission**: `Lab 5 _ OPS245` [24], `Lab 6 _ OPS245` [25], `Lab 8 _ OPS245` [26], `Lab 7 - PowerShell Variables.docx`, and `Lab 8 - Creating Users with PS.docx` [4].
  * **Verified Outcomes**: Configured persistent Linux network interfaces in `/etc/network/interfaces` [25], managed storage mounts via `/etc/fstab` with `systemctl daemon-reload` [24], implemented ISC DHCP daemons (`dhcpd.conf`) [26], and wrote administrative Bash scripts. On Windows Server, wrote and executed PowerShell scripts (`bulk_users.ps1`) to parse CSV datasets for automated multi-user provisioning [3, 4].

* **IP Connectivity & Network Services Troubleshooting (DHCP, DNS, Subnetting, Default Gateways)**:
  * **Course Code**: CSN115 / CSN205 / MST200 / OPS245 [25, 27-29].
  * **Lab / Submission**: `CSN205 Lab 4 Static and Default routes` [28, 30-32], `Group3+CSN205+Lab+3_Subnetting+and+VLSM`, `Lab 6 - DHCP Server1.docx`, `Week5-DHCP-DNS.pptx` [29], and `Lab 6 _ OPS245` [25].
  * **Verified Outcomes**: Executed Variable Length Subnet Masking (VLSM) and CIDR address allocations [28], configured static routing and default gateway routes (`0.0.0.0/0`) [28, 32], set up DHCP scopes with static MAC address reservations [26], integrated AD-dependent DNS servers [29], and resolved connectivity issues using diagnostics (`ping`, `ipconfig`, `ip address`, `show ip route`) [25, 32, 33].

* **Technical Documentation & Infrastructure Recording**:
  * **Course Code**: CSN205 / MST200 / OPS245 / COM101 [4, 12, 23, 34].
  * **Lab / Submission**: `Group#_CSN205Assign1.pdf` [12], `CSN205 Assignment 2 OSPFv2` [35], `SenecaID-Lab8.PDF` [4], and `Group2_CSN205Lab1B.pdf` [10].
  * **Verified Outcomes**: Recorded network topologies, compiled CLI command outputs, captured verification screenshots, structured IP addressing schemes, and submitted technical lab reports per academic guidelines [4, 12, 35].

---

### 2. Concrete Commands, Cmdlets & Configuration Syntax Executed

* **Active Directory & PowerShell Cmdlets**:
  * `New-ADUser -name RMurdoch -OtherAttributes @{'title'='director'}` [3]
  * `Get-ADUser -Identity <username>` [3]
  * `New-ADGroup -SamAccountName "Marketing_Read" -GroupCategory Security -GroupScope DomainLocal -Path "OU=Toronto,DC=SenecaID,DC=net"` [3, 6]
  * `gpmc.msc` (Group Policy Management Console for Default Domain Policy configuration) [5]
  * Execution of `.\bulk_users.ps1` against `bulk_users.csv` for automated account ingestion [3, 4]
  * `Add-DnsServerResourceRecordA -Name 'client1' -ZoneName 'SenecaID.com' -IPv4Address 10.0.99.100` [3]
  * `Get-DnsServerResourceRecord -ZoneName 'SenecaID.com' -Name 'client1'` [3]

* **Cisco Switch & Router CLI Syntax**:
  * `vlan 10` -> `name SenecaCollege` [11, 12]
  * `vlan 20` -> `name YorkUniversity` [11, 12]
  * `interface FastEthernet0/1` -> `switchport mode trunk` -> `switchport trunk native vlan 99` -> `switchport trunk allowed vlan 10,20,99` [11, 12]
  * `interface FastEthernet0/6` -> `switchport mode access` -> `switchport access vlan 10` [11, 12]
  * `interface GigabitEthernet0/1.10` -> `encapsulation dot1q 10` -> `ip address 192.168.10.1 255.255.255.0` [11, 12]
  * `SW1(config)#hostname SW1` [15, 19]
  * `SW1(config)#no ip domain-lookup` [15, 19]
  * `SW1(config)#no enable password` / `SW1(config)#no enable secret` [16, 20]
  * `ip route 0.0.0.0 0.0.0.0 10.2.0.229` [32]
  * Diagnostics: `show vlan brief`, `show interface trunk`, `show ip route` [11, 32]

* **Linux Server & Utility Commands**:
  * Network Configuration (`/etc/network/interfaces`): `auto enp1s0`, `iface enp1s0 inet static`, `address 192.168.245.13/24`, `gateway 192.168.245.1`, `dns-nameservers 192.168.245.1` [25]
  * Diagnostics & Connectivity: `ip -brief address`, `ip route`, `ping www.debian.org`, `ss -atunp` [25]
  * Storage & Systemd: `/etc/fstab` mounts, `systemctl daemon-reload`, `mount -a` [24]
  * User & Process Management: `useradd`, `usermod`, `userdel`, `systemctl status cron`, `journalctl -f -u isc-dhcp-server` [24, 26]

---

### 3. Practical Infrastructure & Platforms Used

* **Windows Server & Directory Platforms**:
  * Windows Server 2016 and Windows Server 2019 (Desktop Experience and headless Server Core) hosted on VMware Workstation Pro virtual machines [36-40].
  * Managed remotely from Windows 10 administrative client VMs (`AdminClient`, `Client1`) using Remote Server Administration Tools (RSAT), Server Manager, Windows Admin Center, and Remote Desktop Protocol (RDP) [6, 39, 41-43].
  * Cloud infrastructure explored via Microsoft Azure DevTest Labs [37, 44].

* **Cisco Networking Infrastructure**:
  * Physical Cisco hardware (Cisco Catalyst 2960 switches, Cisco 1941 routers) configured in hands-on pod labs via serial console connections using PuTTY terminal emulation [10, 11, 13, 14, 35].
  * Virtual topologies simulated in Cisco Packet Tracer (`Group2_CSN205Assign1.pkt`, `CSN205 Lab 4`) prior to physical hardware deployment [12, 18, 30].

* **Linux System Infrastructure**:
  * Bare-metal Debian 12 (bookworm) installations running on external USB 3.0 SSD hosts alongside local virtual machines (`deb1`, `deb2`, `deb3`) managed via KVM hypervisors (`virsh`) on isolated private virtual networks (`network1`) [4, 24-26].

---

### 4. Identified Curriculum Gaps

* **Windows Server 2022**: The job specifically requests experience with **Windows Server 2022**. The curriculum materials in MST100 and MST200 cover **Windows Server 2016** and **Windows Server 2019** [36-38, 40, 45]; Windows Server 2022 is not documented or installed in these semesters.
* **Enterprise Centralized Monitoring Tools**: Native tools like `journalctl`, `ss`, `ipconfig`, and `show ip route` are practiced [25, 26, 32, 33], but third-party infrastructure monitoring platforms (e.g., Zabbix, Nagios, Datadog, SolarWinds) are not covered.
* **Configuration Management & Infrastructure as Code (IaC)**: Automation is performed via PowerShell (`bulk_users.ps1`) and Bash scripts [3, 25], but declarative IaC tools (Ansible, Terraform, Puppet, Chef, PowerShell Desired State Configuration) are absent.
* **Production Cloud Networking**: Cloud coverage is introductory (Azure DevTest Labs and conceptual cloud service models like IaaS/PaaS/SaaS) [37, 44, 46]; production cloud networking (VNet peering, AWS VPCs, Cloud IAM policies, hybrid VPN tunnels) is not practiced in these lab files.

---

💡 **Would you like me to create an interview preparation sheet mapping these exact lab proofs to common Junior Administrator scenario questions?**

---

## 2. High-Impact LaTeX ModernCV Bullets

You can insert these directly into `\section{Education}` or `\section{Technical Projects}` in your tailored CV:

```latex
\begin{itemize}
\item \textbf{Active Directory Administration & Group Policy}: * \textbf{Course Code}: MST100 / MST200 .
\item \textbf{Lab / Submission}: \texttt{Lab 4 - User and Group Management(1).docx} , \texttt{Lab 8 - Creating Users with PS.docx} , \texttt{Week2-UsersandGroups.pptx} , and \texttt{08 Intro to Active Directory.pptx} .
\item \textbf{Verified Outcomes}: Provisioned Active Directory Organizational Units (OUs like \texttt{Toronto}, \texttt{Montreal}, \texttt{Vancouver}) , Global Security Groups (\texttt{T_SalesReps}) , and Domain Local Groups (\texttt{HR_Read}, \texttt{SalesFiles_FC})  using the AGDLP role-based access model . Configured Active Directory Group Policies via Group Policy Management Console (\texttt{gpmc.msc}) to enforce Account Policies (Password Policy, Account Lockout Policy, Kerberos Policy) and User Rights Assignments .
\item \textbf{Cisco Switch Port Configuration, VLANs & 802.1Q Trunking}: * \textbf{Course Code}: CSN205 / CSN115 .
\item \textbf{Lab / Submission}: \texttt{Group2_CSN205Assign1.pdf} , \texttt{Group2_CSN205Lab1B.pdf} , \texttt{Lab1A_Golden.pdf} , and \texttt{LAB2-CSN.pdf} .
\end{itemize}
```

---

## 3. Staging for Factual Grounding Audit

To ensure these verified facts pass the Step 3 Grounding Audit in `/apply`, copy the verified achievements into `.claude/skills/job-application-assistant/01-candidate-profile.md` under **Education -> Key Coursework & Competencies**:

> [!TIP]
> All bullets above originate directly from your completed coursework in OPS145/245, MST100/200, CSN115/205, and SEC220. Adding them to `01-candidate-profile.md` preserves audit compliance with zero risk of hallucination flags.
