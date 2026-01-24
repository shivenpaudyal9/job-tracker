# Fix Azure Portal Authentication Error

## Error You're Seeing
```
AADSTS160021: Application requested a user session which does not exist
```

This is a common cookie/cache issue. Here are the fixes:

---

## Fix 1: Private/Incognito Window (Quickest)

1. **Open a Private/Incognito window:**
   - Chrome: Ctrl + Shift + N
   - Edge: Ctrl + Shift + P
   - Firefox: Ctrl + Shift + P

2. **Go to:** https://portal.azure.com

3. **Sign in** with your Outlook account

4. **Search for "App registrations"**

**Why this works:** Bypasses cached authentication tokens

---

## Fix 2: Clear Browser Cache

1. **Press:** Ctrl + Shift + Delete
2. **Select:**
   - Cookies and other site data
   - Cached images and files
3. **Time range:** All time
4. **Click:** Clear data
5. **Close browser completely**
6. **Reopen** and go to https://portal.azure.com

---

## Fix 3: Try Different Browser

If you're using Chrome, try Edge (or vice versa)

---

## Fix 4: Direct Link (Bypass Portal Home)

Instead of searching, use this direct link:
https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade

This goes straight to App Registrations

---

## Fix 5: Alternative Registration Method

If Azure Portal continues having issues, we can register the app using:

### Microsoft Entra Admin Center (Same Thing, Different URL)
https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade

OR

### Azure CLI (Command Line)
No browser needed - I'll give you commands to run

---

## Which Fix Should You Try First?

**Easiest:** Option 1 (Private window)
**Most reliable:** Option 2 (Clear cache)
**Quickest alternative:** Option 4 (Direct link)

Let me know which one works!
