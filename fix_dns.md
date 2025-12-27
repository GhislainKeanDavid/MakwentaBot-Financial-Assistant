# Fix DNS Resolution Issue

## Problem
Your Windows system DNS cannot resolve `db.bggywlojaocixdpelyts.supabase.co`, but Google DNS (8.8.8.8) can.

## Solution 1: Use Supabase Connection Pooler (Recommended)

1. Go to Supabase Dashboard → Settings → Database
2. Look for **"Connection Pooling"** or **"Pooler"** section
3. Copy the pooler connection string (should look like):
   ```
   postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
4. Update your `.env` file with this new URL
5. Test: `python test_database_connection.py`

## Solution 2: Change Windows DNS to Google DNS

If connection pooler doesn't exist, change your DNS settings:

### Method A: PowerShell (Quick)

1. Open PowerShell as Administrator (Right-click Start → Windows PowerShell (Admin))
2. Run these commands:

```powershell
# Find your network adapter name
Get-NetAdapter | Where-Object {$_.Status -eq "Up"}

# Set DNS to Google DNS (replace "Ethernet" with your adapter name)
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses ("8.8.8.8","8.8.4.4")

# Or for Wi-Fi:
Set-DnsClientServerAddress -InterfaceAlias "Wi-Fi" -ServerAddresses ("8.8.8.8","8.8.4.4")

# Flush DNS cache
Clear-DnsClientCache
```

### Method B: GUI (Manual)

1. Press `Win + R`, type `ncpa.cpl`, press Enter
2. Right-click your active network connection → Properties
3. Select "Internet Protocol Version 4 (TCP/IPv4)" → Properties
4. Select "Use the following DNS server addresses"
5. Enter:
   - **Preferred DNS:** `8.8.8.8`
   - **Alternate DNS:** `8.8.4.4`
6. Click OK, OK
7. Open Command Prompt and run: `ipconfig /flushdns`

## Solution 3: Add to hosts file (Temporary Workaround)

1. Open Notepad as Administrator
2. File → Open: `C:\Windows\System32\drivers\etc\hosts`
3. Add this line at the bottom:
   ```
   2406:da14:271:9903:e583:2b42:9377:fb29 db.bggywlojaocixdpelyts.supabase.co
   ```
4. Save and close
5. Test: `python diagnose_supabase.py`

## Test After Each Solution

Run this to test:
```bash
python test_database_connection.py
```

## Which Solution Should You Use?

1. **Try Solution 1 first** (Connection Pooler) - This is the modern Supabase way
2. **If no pooler exists**, try Solution 2 (Change DNS to Google)
3. **Solution 3 is a quick workaround** but not permanent

Let me know which works!
