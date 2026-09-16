"""
Source Catalog and Course Mapping for Seneca CTY Year 1 (Semesters 1 and 2).

Indexes the 133 curriculum sources in Gemini Notebook "Semester 1 and 2 CTY"
(ID: e32153b2-e906-4762-a8c3-8b96fbf093b4) into course clusters:
- OPS145: Introduction to Linux (Bash scripting, CLI, file permissions)
- OPS245: Open Systems Server (CentOS/RHEL, systemd, storage, services, LVM)
- MST100: Introduction to Microsoft Services (Windows Server fundamentals, CLI, PowerShell intro)
- MST200: Microsoft Server Administration (Active Directory DS, GPO, DNS, DHCP, PowerShell automation, Azure DevTest Labs)
- CSN115: Introduction to Computers and Networks (Hardware, PC assembly, OSI/TCP-IP basics, subnetting)
- CSN205: Static Networks & Cisco Routing/Switching (Cisco IOS, VLANs, 802.1Q, Inter-VLAN routing, OSPFv2, IPv4 ACLs, Packet Tracer)
- SEC220: System and Network Security (Wireshark sniffing, asymmetric encryption, host hardening, access control, password cracking)
- SPS120: Strategic Problem Solving
- COM101: Communicating Across Contexts
"""

from typing import Dict, List, Any, Optional

COURSE_METADATA = {
    "OPS145": {
        "title": "Introduction to Linux",
        "keywords": ["linux", "bash", "shell", "chmod", "chown", "grep", "awk", "sed", "cli", "file permissions"],
    },
    "OPS245": {
        "title": "Open Systems Server (Linux)",
        "keywords": ["centos", "rhel", "systemd", "storage", "lvm", "nfs", "samba", "ssh", "cron", "apache", "services", "selinux"],
    },
    "MST100": {
        "title": "Introduction to Microsoft Services",
        "keywords": ["windows server", "installing server", "commandline", "powershell", "intro to active directory"],
    },
    "MST200": {
        "title": "Microsoft Server Administration & Active Directory",
        "keywords": ["active directory", "ad ds", "gpo", "group policy", "dns", "dhcp", "powershell", "bulk_users", "azure", "remote admin", "domain controller"],
    },
    "CSN115": {
        "title": "Introduction to Computer & Networks",
        "keywords": ["motherboard", "processor", "memory", "power supply", "hardware", "number systems", "binary", "hexadecimal", "osi model", "tcp/ip"],
    },
    "CSN205": {
        "title": "Static Networks & Cisco Routing/Switching",
        "keywords": ["cisco", "ios", "vlan", "trunk", "802.1q", "inter-vlan", "routing", "ospf", "ospfv2", "acl", "access list", "packet tracer", "switch", "router", "spanning tree", "rstp", "pvst"],
    },
    "SEC220": {
        "title": "System and Network Security",
        "keywords": ["security", "sniffing", "wireshark", "encryption", "firewall", "iptables", "password cracking", "host hardening", "access control", "phishing", "network scanning", "nmap"],
    },
    "SPS120": {
        "title": "Strategic Problem Solving",
        "keywords": ["problem solving", "troubleshooting", "methodology", "incident"],
    },
    "COM101": {
        "title": "Communicating Across Contexts",
        "keywords": ["technical documentation", "communication", "reporting"],
    }
}


def classify_source(title: str) -> str:
    """Assigns a course code to a source title based on naming patterns."""
    t_lower = title.lower()

    # Explicit course tags
    if "ops245" in t_lower or "ops 245" in t_lower:
        return "OPS245"
    if (
        "csn205" in t_lower
        or "ccna" in t_lower
        or "ospf" in t_lower
        or "lab2-csn" in t_lower
        or "rstp" in t_lower
        or "spanning tree" in t_lower
        or "ip routing" in t_lower
        or "switch port security" in t_lower
        or "implementing dhcp" in t_lower
    ):
        return "CSN205"
    if "sec220" in t_lower or "sec 220" in t_lower:
        return "SEC220"
    if (
        "csn115" in t_lower
        or "csn 115" in t_lower
        or "introduction to" in t_lower
        or "_introduction" in t_lower
    ):
        # Disambiguate "introduction to cloud computing" -> MST200
        if "cloud computing" in t_lower:
            return "MST200"
        return "CSN115"
    if (
        "intro to mst" in t_lower
        or "01 intro to mst" in t_lower
        or "02 installing server" in t_lower
        or "03 intro to windows" in t_lower
        or "04 commandline" in t_lower
        or "powershell" in t_lower
        and ("05" in t_lower or "06" in t_lower)
        or "07 users and groups" in t_lower
        or "07.5 intro" in t_lower
        or "08 intro to active directory" in t_lower
    ):
        return "MST100"
    if (
        "week1-review" in t_lower
        or "week2-users" in t_lower
        or "week3-managing" in t_lower
        or "week4-printing" in t_lower
        or "week5-dhcp" in t_lower
        or "week8-powershell" in t_lower
        or "week10-powershell" in t_lower
        or "week12" in t_lower
        or "azure demo" in t_lower
        or "azure server configuration" in t_lower
        or "dhcp server" in t_lower
        or "creating users with ps" in t_lower
        or "cloud computing" in t_lower
    ):
        return "MST200"
    if "sps120" in t_lower or "sps 120" in t_lower:
        return "SPS120"
    if "com101" in t_lower or "com 101" in t_lower:
        return "COM101"

    # Lab and practice files
    if any(t_lower.startswith(prefix) for prefix in ["wk08", "wk09", "wk10", "wk11"]):
        return "OPS245"
    if any(t_lower.startswith(prefix) for prefix in ["wk2", "wk3", "wk4", "wk5", "wk6"]):
        return "OPS145"

    # Generic Lab files in MST200
    if (
        "lab 1 - prelab" in t_lower
        or "lab 2 - creating vms" in t_lower
        or "lab 3 - ad and" in t_lower
        or "lab 4 - user and" in t_lower
        or "lab 5 - file and" in t_lower
        or "lab 6 - dhcp" in t_lower
        or "lab 7 - powershell" in t_lower
        or "lab 8 - creating" in t_lower
        or "lab 9 - intro" in t_lower
        or "lab 10 - azure" in t_lower
    ):
        return "MST200"

    if "lab1a_golden" in t_lower:
        return "CSN205"

    return "GENERAL"


class SourceCatalog:
    """Manages course-indexed source documents from the Gemini Notebook."""

    def __init__(self, raw_sources: List[Dict[str, Any]]):
        self.sources = raw_sources
        self.by_course: Dict[str, List[Dict[str, Any]]] = {}
        for s in raw_sources:
            title = s.get("title", "")
            sid = s.get("id", "")
            course = classify_source(title)
            s_entry = {"id": sid, "title": title, "course": course}
            self.by_course.setdefault(course, []).append(s_entry)

    def get_sources_for_course(self, course_code: str) -> List[Dict[str, Any]]:
        """Returns all sources classified under a specific course."""
        return self.by_course.get(course_code.upper(), [])

    def get_source_ids_for_courses(self, course_codes: List[str]) -> List[str]:
        """Returns unique source IDs for a given set of course codes."""
        ids: List[str] = []
        for code in course_codes:
            for item in self.get_sources_for_course(code):
                ids.append(item["id"])
        return ids

    def match_courses_for_query(self, query_text: str) -> List[str]:
        """Identifies relevant course codes based on keyword matching in query text."""
        q = query_text.lower()
        matched: List[str] = []
        for code, meta in COURSE_METADATA.items():
            for kw in meta["keywords"]:
                if kw in q:
                    if code not in matched:
                        matched.append(code)
                    break
        return matched

    def summary(self) -> Dict[str, int]:
        """Returns source counts per course code."""
        return {k: len(v) for k, v in sorted(self.by_course.items())}
