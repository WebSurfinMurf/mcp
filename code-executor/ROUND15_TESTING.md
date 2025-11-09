# Round 15 Testing Instructions

## Quick Summary

**What we fixed**: The stdio bridge was exiting after one request instead of staying alive in a persistent loop.

**Solution**: Created `code-executor-stdio-v2.py` with bidirectional stdin↔docker↔stdout loop using threading.

**Manual test result**: ✅ PASSED - Returns all 4 tools correctly

## When Claude Code Restarts

Send this message to the new session:

```
Read /home/administrator/projects/admin/AINotes/temp.md and follow Round 15 instructions
```

## The 3 Tests to Run

### Test 1: Minimal Server
```
mcp__code-executor-test__test_tool
```
This proves config loading works.

### Test 2: Code Executor List Tools
```
mcp__code-executor__list_mcp_tools
```
Should return ~67 tools from all 10 MCP servers.

### Test 3: Execute Simple Code
```
mcp__code-executor__execute_code with {"code": "console.log(2+2)"}
```
Should return `{"output": "4\n", ...}`

## Expected Results

✅ **All 3 pass** = Victory! Phase 2 complete!
❌ **Test 1 fails** = Config loading issue (restart didn't work)
❌ **Test 2 fails, Test 1 works** = v2 has a bug (threading issue?)
❌ **All fail** = Need deeper investigation

## Files Created

- `test-minimal-mcp.py` - Minimal working MCP server (pure Python)
- `code-executor-stdio-v2.py` - Fixed bidirectional bridge (persistent loop)
- Config updated to point to v2

## Scientific Discovery

The breakthrough came from your suggestion to start minimal and add incrementally!

**Key insight**: Working MCP servers use `while True` loop reading stdin, not `subprocess.Popen().wait()` which exits after one request.

## Confidence Level

🟢 **85%** confident v2 will work:
- Manual test passed ✅
- Follows proven mcp-bridge.py pattern ✅
- Uses standard threading for bidirectional pipes ✅
- Only risk: Docker exec stdin behavior under load (untested)

---

**Ready to test!** Exit this session, restart Claude Code, and run the 3 tests above.
