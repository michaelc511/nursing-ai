# Connect NurseOps Now to Claude Cowork

**Status: done 2026-11-14.** Request headers were under **Advanced**; all 7 tools listed; test question and scheduled task worked on the live app. Demo use: `docs/demo/4-demo-script.md` #5 and `docs/demo/1-short_script.md` #5.

Desktop setup steps for idea 1 (scheduled intake) and idea 4 (ask about your operations). Anthropic says the token option in Part 3 is a limited beta, so your account may not show it.

Never paste the token into a chat or commit it. Enter it only in the connector dialog.

## Part 1: Install

1. Go to [claude.com/download](https://claude.com/download) and download the Mac app.
2. Open the downloaded file and drag **Claude** into **Applications**.
3. Open **Claude** and sign in with your Google account. Cowork needs a paid Claude plan.

## Part 2: Get your token

4. Press **Cmd + Space**, type `Terminal`, and press **Enter**.
5. Paste this and press **Enter**:

```
grep MCP_TOKEN ~/nurseops-fly.txt
```

6. Copy only the long text after `MCP_TOKEN=`. Keep this window open.

## Part 3: Add the connector

7. In Claude, open **Customize**, then **Connectors**. If you can't find it, open [claude.ai/customize/connectors](https://claude.ai/customize/connectors) in your browser instead.
8. Click **Add**, then **Add custom connector**.
9. In the name box, type `Prior Auth`.
10. In the URL box, paste `https://nurseops-now.fly.dev/mcp`.
11. Click **Continue**.
12. Under **Authentication**, choose **No sign-in**.
13. Look for **Request headers**. If you don't see it, open **Advanced**.

**Stop here if there's no Request headers section.** The app would need a different sign-in method (OAuth).

14. Choose `authorization` as the header name.
15. In the value box, type `Bearer`, press the space bar once, then paste your token.
16. Mark it **Required**, then click **Add**.

## Part 4: Test it (idea 4: ask about your operations)

17. Switch to **Cowork** in the Claude app and start a new task.
18. Paste this and press **Enter**:

```
Use the Prior Auth connector. What's our override rate, and which cases are stuck more than 2 days?
```

19. If it asks permission to use a tool, click **Allow**.

The app may take a little while to wake up.

## Part 5: Scheduled intake (idea 1)

20. Click **Scheduled**, then **New task**, then **Set up manually**.
21. Name it `Prior auth intake`, set the frequency to **Manually** for now, and paste this prompt:

```
Use the Prior Auth connector. Run run_all to process new prior auth requests. Then call get_metrics and get_stuck_cases with days=2. Report: number of new cases, how many are Incomplete (with missing items), how many are Ready for Review by tier, and any stuck cases. Do not make approval or denial decisions; those are done by nurses in the web UI.
```

22. Click **Save**.
23. So it has work to do, paste this in Terminal to add the 3 sample requests:

```
fly ssh console --app nurseops-now -C "cp /app/data/samples/72148_a_complete.pdf /app/data/samples/73721_b_missing_pt.pdf /app/data/samples/70551_c_not_met.pdf /data/inbox/"
```

Run it once; it prints only the "Connecting… complete" line when it works. If it says "no started VMs", the app is asleep: open https://nurseops-now.fly.dev in your browser to wake it, then run it again.

24. Open the task in **Scheduled** and run it now. It reviews those 3 on real Claude, for about $0.30, and they appear as new cases alongside the existing 3.

## Sources

- [Add a connector that isn't in the directory](https://claude.com/docs/connectors/custom/remote-mcp)
- [Schedule recurring tasks in Claude Cowork](https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork)
- [Get started with Claude Cowork](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork?b7eea976_page=2)
