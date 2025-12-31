# 🎯 OASE Daily Suggestions Review - Apple Shortcuts Integration

A native macOS Shortcuts integration that surfaces automation suggestions from OASE (Observational Automation Suggestion Engine) via FoKS.

---

## 📋 Overview

This shortcut provides a **first-class macOS experience** for reviewing automation suggestions. It:

- ✅ Queries FoKS for OASE suggestions
- ✅ Displays formatted results in native macOS UI
- ✅ Provides safe, read-only review (no execution)
- ✅ Handles OASE offline gracefully
- ✅ Works entirely on macOS (no iOS required)

---

## 🎯 Goal

Answer the question: **"Do I have any automation suggestions worth reviewing today?"**

---

## 📋 Prerequisites

- ✅ FoKS backend running at `http://localhost:8000`
- ✅ OASE service running (or gracefully handles offline)
- ✅ macOS Shortcuts app installed
- ✅ Network access to localhost

---

## 🔹 Step-by-Step Shortcut Creation

### Step 1: Create New Shortcut

1. Open **Shortcuts** app (macOS)
2. Click **"+"** (top right) to create new shortcut
3. Name it: **"OASE Daily Suggestions"**
4. Set icon: Choose automation/lightbulb icon (optional)

---

### Step 2: Add HTTP Request Action

1. Search for: **"Get Contents of URL"**
2. Add the action
3. Configure:
   - **URL**: `http://localhost:8000/oase/suggestions/today`
   - **Method**: `GET` (default)
   - **Headers**: None required
   - **Show When Run**: ✅ Enabled (to see response)

**Save result in variable**: `API Response`

---

### Step 3: Parse JSON Response

1. Search for: **"Get Dictionary Value"**
2. Add the action
3. Configure:
   - **Dictionary**: `API Response` (from Step 2)
   - **Key**: `has_suggestions`
4. Save in variable: `Has Suggestions`

---

### Step 4: Branch Logic - Check for Suggestions

1. Search for: **"If"** action
2. Add the action
3. Configure:
   - **Input**: `Has Suggestions`
   - **Condition**: `is` `true`

This creates two branches:
- **If** (has suggestions)
- **Otherwise** (no suggestions)

---

### Step 5A: "Otherwise" Branch - No Suggestions

**When `has_suggestions = false`:**

1. In the **Otherwise** branch:
2. Search for: **"Show Notification"**
3. Configure:
   - **Title**: `OASE Suggestions`
   - **Body**: `No automation suggestions today 🎉`
   - **Sound**: Optional (e.g., "Glass" for positive feedback)

**End of Otherwise branch**

---

### Step 5B: "If" Branch - Has Suggestions

**When `has_suggestions = true`:**

#### 5B.1: Extract Suggestions Array

1. Search for: **"Get Dictionary Value"**
2. Configure:
   - **Dictionary**: `API Response`
   - **Key**: `suggestions`
3. Save in variable: `Suggestions List`

#### 5B.2: Extract Count

1. Search for: **"Get Dictionary Value"**
2. Configure:
   - **Dictionary**: `API Response`
   - **Key**: `count`
3. Save in variable: `Suggestion Count`

#### 5B.3: Format Suggestions Text

1. Search for: **"Repeat with Each"**
2. Configure:
   - **Input**: `Suggestions List`
3. Inside the loop:

   **a) Extract suggestion fields:**
   - **Get Dictionary Value**: `summary` → Save as `Summary`
   - **Get Dictionary Value**: `confidence` → Save as `Confidence`
   - **Get Dictionary Value**: `estimated_time_saved_min_per_week` → Save as `Time Saved`

   **b) Format confidence as percentage:**
   - **Calculate**: `Confidence` × `100`
   - Save as `Confidence Percent`

   **c) Build formatted line:**
   - **Text** action:
     ```
     • Summary: [Summary]
       Confidence: [Confidence Percent]%
       Time saved: ~[Time Saved] min/week
     ```
   - Save in variable: `Formatted Suggestion`

   **d) Append to results:**
   - **Text** action: Append `Formatted Suggestion` to running text
   - Save in variable: `All Suggestions` (accumulated)

4. After loop, create final message:
   - **Text** action:
     ```
     📊 OASE Suggestions ([Suggestion Count] found)

     [All Suggestions]

     ---
     Review these patterns and consider automation opportunities.
     ```
   - Save as `Final Message`

#### 5B.4: Show Formatted Results

1. Search for: **"Choose from List"**
2. Configure:
   - **Prompt**: `Final Message`
   - **Select Multiple**: ✅ Enabled
   - **Input**: `Suggestions List` (to allow selection)

3. Save selection in variable: `Selected Suggestions`

#### 5B.5: User Action Menu

1. Search for: **"Choose from Menu"**
2. Configure with options:
   - **"Review Later"** → Do nothing (just close)
   - **"Open FoKS Dashboard"** → Open URL: `http://localhost:8000/docs`
   - **"Copy Summaries"** → Copy `Final Message` to clipboard

3. For each menu option, add corresponding action:
   - **"Review Later"**: No action (shortcut ends)
   - **"Open FoKS Dashboard"**: **Open URLs** action → `http://localhost:8000/docs`
   - **"Copy Summaries"**: **Copy to Clipboard** action → `Final Message`

**End of If branch**

---

### Step 6: Error Handling (Optional but Recommended)

**Before Step 2 (HTTP Request), add:**

1. Search for: **"Try"** action
2. Wrap the HTTP request and all parsing in the **Try** block
3. Add **"Otherwise"** (catch) block:
   - **Show Notification**:
     - **Title**: `OASE Error`
     - **Body**: `Failed to fetch suggestions. Check if FoKS is running.`

---

## 📸 Visual Flow Diagram

```
OASE Daily Suggestions
│
├── Get Contents of URL
│   └── http://localhost:8000/oase/suggestions/today
│
├── Get Dictionary Value (has_suggestions)
│
├── If (has_suggestions == true)
│   │
│   ├── Get Dictionary Value (suggestions)
│   ├── Get Dictionary Value (count)
│   │
│   ├── Repeat with Each (suggestions)
│   │   ├── Extract: summary, confidence, time_saved
│   │   ├── Format as text
│   │   └── Append to results
│   │
│   ├── Format final message
│   ├── Choose from List (show suggestions)
│   └── Choose from Menu (user actions)
│       ├── Review Later
│       ├── Open FoKS Dashboard
│       └── Copy Summaries
│
└── Otherwise (has_suggestions == false)
    └── Show Notification: "No suggestions today 🎉"
```

---

## 🧪 Testing

### Test Case 1: OASE Running with Suggestions

1. Ensure OASE is running and has recent patterns
2. Run shortcut
3. **Expected**: Formatted list of suggestions with menu options

### Test Case 2: OASE Running, No Suggestions

1. Ensure OASE is running but no recent patterns
2. Run shortcut
3. **Expected**: Notification "No automation suggestions today 🎉"

### Test Case 3: OASE Offline

1. Stop OASE service
2. Run shortcut
3. **Expected**: Error notification or graceful message

### Test Case 4: FoKS Offline

1. Stop FoKS backend
2. Run shortcut
3. **Expected**: Error notification about FoKS not running

---

## 📝 Example Outputs

### Output 1: With Suggestions

```
📊 OASE Suggestions (2 found)

• Summary: Frequent use of Cursor (10 times)
  Confidence: 82%
  Time saved: ~16 min/week

• Summary: Use of Chrome at 14:00 (8 times)
  Confidence: 75%
  Time saved: ~12 min/week

---
Review these patterns and consider automation opportunities.
```

**Menu Options:**
- Review Later
- Open FoKS Dashboard
- Copy Summaries

### Output 2: No Suggestions

**Notification:**
```
Title: OASE Suggestions
Body: No automation suggestions today 🎉
```

---

## 🔧 Configuration

### Change FoKS Port

If FoKS runs on a different port, update Step 2:
- **URL**: `http://localhost:<port>/oase/suggestions/today`

### Change Confidence Threshold

The endpoint filters to confidence ≥ 0.5. To change:
- Modify FoKS endpoint (not recommended for this feature)
- Or filter in Shortcut after receiving response

---

## 🚨 Safety Features

- ✅ **Read-only**: No automation execution
- ✅ **No state changes**: Does not mark suggestions as reviewed
- ✅ **No persistence**: Does not save any data
- ✅ **Graceful failures**: Handles OASE/FoKS offline
- ✅ **Human approval**: All actions require user selection

---

## 📦 Installation

1. Follow **Step-by-Step Shortcut Creation** above
2. Or import from JSON (see next section)
3. Test with all three test cases
4. Add to Dock or Menu Bar for quick access (optional)

---

## 🔄 Updates

If the FoKS API response format changes, update:
- **Step 3**: Dictionary key extraction
- **Step 5B.3**: Field names in formatting

---

## 🐛 Troubleshooting

### "Failed to connect"

- ✅ Check FoKS is running: `curl http://localhost:8000/health`
- ✅ Check OASE is running: `curl http://localhost:8000/health` (if OASE on same port)

### "No suggestions" when expecting some

- ✅ Check OASE has recent patterns: `curl http://localhost:8000/api/knowledge-units/`
- ✅ Verify confidence threshold (≥ 0.5)
- ✅ Check time window (last 24 hours)

### Shortcut shows error

- ✅ Enable "Show When Run" in HTTP request action
- ✅ Check JSON parsing steps match response structure
- ✅ Verify variable names are consistent

---

## 📚 Related Documentation

- [FoKS API Reference](../../docs/API_REFERENCE.md)
- [OASE Architecture](../../../OASE/docs/ARCHITECTURE.md)
- [Shortcuts Setup Guide](../../docs/SHORTCUT_SETUP.md)

---

## ✅ Validation Checklist

- [ ] Shortcut runs without errors
- [ ] Shows suggestions when OASE has patterns
- [ ] Shows "no suggestions" when appropriate
- [ ] Handles OASE offline gracefully
- [ ] Menu options work correctly
- [ ] No side effects (read-only)
- [ ] Works on macOS (tested)

---

**Last Updated**: 2025-12-26  
**Version**: 1.0  
**Status**: ✅ Ready for Use

