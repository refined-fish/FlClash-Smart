#!/usr/bin/env python3
"""
Conflict resolver for merging vernesong/mihomo (branch Alpha, Smart core)
into chen08209/Clash.Meta (branch FlClash).
"""

import os
import re
import sys

def resolve_update_geo(meta_dir: str):
    path = os.path.join(meta_dir, "component", "updater", "update_geo.go")
    if not os.path.exists(path):
        print(f"[!] File not found: {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # In update_geo.go, HEAD contains the FlClash geo status notifications.
    # Keep HEAD side for all conflicts.
    resolved = re.sub(r'<<<<<<< HEAD\r?\n([\s\S]*?)=======\r?\n[\s\S]*?>>>>>>> [^\r\n]*\r?\n', r'\1', content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(resolved)
    print(f"[+] Resolved conflicts in {path}")

def resolve_manager(meta_dir: str):
    path = os.path.join(meta_dir, "tunnel", "statistic", "manager.go")
    if not os.path.exists(path):
        print(f"[!] File not found: {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    mgr_target = """\tconnections        xsync.Map[string, Tracker]
\tsmartTarget        xsync.Map[string, *xsync.Map[string, bool]]
\tuploadTemp         atomic.Int64
\tdownloadTemp       atomic.Int64
\tuploadBlip         atomic.Int64
\tdownloadBlip       atomic.Int64
\tuploadTotal        atomic.Int64
\tdownloadTotal      atomic.Int64
\tproxyUploadTemp    atomic.Int64
\tproxyDownloadTemp  atomic.Int64
\tproxyUploadBlip    atomic.Int64
\tproxyDownloadBlip  atomic.Int64
\tproxyUploadTotal   atomic.Int64
\tproxyDownloadTotal atomic.Int64
\tpid                int32
\tmemory             uint64"""

    resolved = re.sub(r'<<<<<<< HEAD\r?\n[\s\S]*?>>>>>>> [^\r\n]*', mgr_target, content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(resolved)
    print(f"[+] Resolved conflicts in {path}")

def resolve_tracker(meta_dir: str):
    path = os.path.join(meta_dir, "tunnel", "statistic", "tracker.go")
    if not os.path.exists(path):
        print(f"[!] File not found: {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # In tcpTracker / udpTracker structs
    tracker_struct_pattern = r'<<<<<<< HEAD\r?\n\tdirect        bool `json:"-"`\r?\n=======\r?\n\r?\n\tuploadBucketWindow   \*bucketWindow\r?\n\tdownloadBucketWindow \*bucketWindow\r?\n>>>>>>> [^\r\n]*'
    tracker_struct_replace = '\tdirect               bool `json:"-"`\n\tuploadBucketWindow   *bucketWindow\n\tdownloadBucketWindow *bucketWindow'
    content = re.sub(tracker_struct_pattern, tracker_struct_replace, content)

    # In NewTCPTracker start
    tcp_start_pattern = r'<<<<<<< HEAD\r?\n\ttt := &tcpTracker\{\r?\n=======\r?\n\ttrackerUUID := utils\.NewUUIDV4\(\)\r?\n\r?\n\tmetadata\.UUID = trackerUUID\.String\(\)\r?\n\r?\n\tt := &tcpTracker\{\r?\n>>>>>>> [^\r\n]*'
    tcp_start_replace = """\ttrackerUUID := utils.NewUUIDV4()

\tmetadata.UUID = trackerUUID.String()

\ttt := &tcpTracker{"""
    content = re.sub(tcp_start_pattern, tcp_start_replace, content)

    # In NewTCPTracker and NewUDPTracker fields
    fields_pattern = r'<<<<<<< HEAD\r?\n\t\tpushToManager: pushToManager,\r?\n\t\tdirect:        IsDirect\(conn\.Chains\(\)\.Last\(\)\),\r?\n=======\r?\n\t\tpushToManager:        pushToManager,\r?\n\t\tuploadBucketWindow:   newBucketWindow\(10, 100\),\r?\n\t\tdownloadBucketWindow: newBucketWindow\(10, 100\),\r?\n>>>>>>> [^\r\n]*'
    fields_replace = """\t\tpushToManager:        pushToManager,
\t\tdirect:               IsDirect(conn.Chains().Last()),
\t\tuploadBucketWindow:   newBucketWindow(10, 100),
\t\tdownloadBucketWindow: newBucketWindow(10, 100),"""
    content = re.sub(fields_pattern, fields_replace, content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] Resolved conflicts in {path}")

def main():
    meta_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"Resolving Clash.Meta merge conflicts in: {meta_dir}")
    resolve_update_geo(meta_dir)
    resolve_manager(meta_dir)
    resolve_tracker(meta_dir)

    # Check if any conflict markers remain in the repository
    conflict_found = False
    for root, _, files in os.walk(meta_dir):
        for file in files:
            if file.endswith(".go"):
                full_path = os.path.join(root, file)
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                    if "<<<<<<<" in text and ">>>>>>>" in text:
                        print(f"[ERROR] Conflict marker still present in {full_path}")
                        conflict_found = True

    if conflict_found:
        print("[!] Merge resolution failed: unresolved conflicts remaining.")
        sys.exit(1)
    else:
        print("[+] All conflicts successfully resolved!")

if __name__ == "__main__":
    main()
