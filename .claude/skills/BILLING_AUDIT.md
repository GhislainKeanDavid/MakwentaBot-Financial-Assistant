# Billing Audit Skill

**Purpose**: Comprehensive audit of Google Cloud billing, subscriptions, and hidden charges to minimize overspending.

**Triggers**: Keywords like "billing", "charges", "subscription", "costs", "spending", "budget", "audit billing", "check costs"

## Objectives

1. **Billing Overview**: Get current month costs and breakdown by service
2. **Hidden Charges Detection**: Identify unexpected or hidden costs
3. **Subscriptions Inventory**: List all active subscriptions and recurring charges
4. **Cost Optimization**: Recommend ways to reduce spending
5. **Resource Audit**: Inventory all billable resources
6. **Budget Status**: Check budget alerts and spending trends

## Audit Checklist

### 1. Billing Overview
```bash
# Get current month billing summary
gcloud billing accounts list
gcloud billing projects describe makwentabot --format=json

# Get cost breakdown by service (requires billing export setup)
# Note: Direct billing API access requires additional permissions
```

**What to check**:
- Total costs for current month vs previous month
- Unexpected spikes in spending
- Services consuming the most budget

---

### 2. Active Services Audit

```bash
# List all enabled services/APIs
gcloud services list --enabled --project=makwentabot

# Check Cloud Run services
gcloud run services list --project=makwentabot --platform=managed --region=asia-southeast1

# List Container Registry images
gcloud container images list --repository=gcr.io/makwentabot

# Check for old/unused revisions
gcloud run revisions list --service=makwenta-bot-service --region=asia-southeast1 --project=makwentabot
```

**What to look for**:
- ✅ **Cloud Run**: Check if CPU allocation is "CPU is only allocated during request processing" (cost-efficient)
- ⚠️ **Old Revisions**: Cloud Run keeps old revisions which may consume storage
- ⚠️ **Container Images**: Old images in GCR cost storage fees ($0.026/GB/month)
- ⚠️ **Enabled APIs**: Some APIs have per-call costs (e.g., Maps, Vision, Translation)

---

### 3. Hidden Charges Detection

```bash
# Check Secret Manager secrets (charged per access + storage)
gcloud secrets list --project=makwentabot

# Check for storage buckets (can have hidden egress costs)
gsutil ls -p makwentabot

# Check Cloud Run service configuration for cost traps
gcloud run services describe makwenta-bot-service --region=asia-southeast1 --format=json
```

**Common Hidden Charges**:
1. **Network Egress**: Data transfer OUT of Google Cloud (esp. to non-Google destinations)
   - Cloud Run → External API calls
   - Download from GCR
   - Webhook responses to Telegram servers

2. **Secret Manager**:
   - $0.06 per 10,000 secret access operations
   - $0.003 per secret version per month
   - **Check**: How many secrets? How often accessed?

3. **Cloud Run**:
   - CPU allocation mode: "Always allocated" vs "Request-based" (huge cost difference!)
   - Container instance idle time
   - Cold start frequency

4. **Container Registry (GCR)**:
   - Storage: $0.026/GB/month
   - Egress: Charges when pulling images
   - **Check**: How many old image versions?

5. **Cloud Logging**:
   - First 50 GB/month free, then $0.50/GB
   - **Check**: Log volume and retention settings

---

### 4. Subscriptions & Third-Party Services

**External Subscriptions** (not in GCP billing):
1. **Supabase Database**:
   - Check: https://supabase.com/dashboard/project/_/settings/billing
   - Free tier: 500 MB database, 1 GB file storage, 2 GB bandwidth
   - Paid tier starts at $25/month

2. **OpenAI API**:
   - Check: https://platform.openai.com/usage
   - GPT-4o-mini: ~$0.15/$0.60 per 1M tokens (input/output)
   - **Monitor**: Token usage trends

3. **Telegram Bot**: Free (no charges)

4. **Domain/DNS** (if applicable):
   - Google Domains or other registrar
   - Renewal dates

**GCP Services** (in GCP billing):
```bash
# List all enabled services that may have costs
gcloud services list --enabled --filter="NAME:(cloudrun OR secretmanager OR logging OR monitoring OR containerregistry)" --project=makwentabot
```

---

### 5. Cost Optimization Recommendations

**Immediate Actions**:
1. **Delete Old Container Images**:
   ```bash
   # List images with creation time
   gcloud container images list-tags gcr.io/makwentabot/makwenta-bot --format="get(digest,timestamp.datetime)" --limit=999

   # Delete images older than 30 days (keeps last 10)
   # CAREFUL: Review before running!
   gcloud container images list-tags gcr.io/makwentabot/makwenta-bot \
     --format="get(digest)" --filter="timestamp.datetime < $(date -d '30 days ago' --iso-8601)" \
     | head -n -10 \
     | xargs -I {} gcloud container images delete "gcr.io/makwentabot/makwenta-bot@{}" --quiet
   ```

2. **Delete Old Cloud Run Revisions**:
   ```bash
   # Cloud Run keeps all revisions by default
   # Delete revisions not serving traffic
   gcloud run revisions list --service=makwenta-bot-service --region=asia-southeast1 \
     --filter="status.conditions.type=Active AND status.conditions.status=False" \
     --format="value(metadata.name)"
   ```

3. **Verify Cloud Run CPU Allocation**:
   ```bash
   # Should be "CPU is only allocated during request processing"
   gcloud run services describe makwenta-bot-service --region=asia-southeast1 --format="value(spec.template.spec.containerConcurrency)"
   ```

4. **Set Budget Alerts**:
   ```bash
   # Check if budget alerts are configured
   gcloud billing budgets list --billing-account=<YOUR_BILLING_ACCOUNT_ID>
   ```

**Cost-Saving Strategies**:
- ✅ Use Cloud Run "request-based" CPU allocation (not "always allocated")
- ✅ Set minimum instances to 0 (allow scaling to zero)
- ✅ Configure max instances to prevent runaway costs
- ✅ Delete old container images (keep last 5-10)
- ✅ Enable log exclusion filters to reduce logging costs
- ✅ Use free tier quotas: 2M requests/month on Cloud Run, 50GB logs/month
- ✅ Monitor OpenAI API token usage (switch to cheaper models if possible)

---

### 6. Resource Inventory & Costs

**Full Resource List**:
```bash
# Cloud Run services
gcloud run services list --project=makwentabot --platform=managed

# Secrets (charged per version + access)
gcloud secrets list --project=makwentabot

# Storage buckets
gsutil ls -p makwentabot

# IAM service accounts
gcloud iam service-accounts list --project=makwentabot

# Enabled APIs (some have per-call costs)
gcloud services list --enabled --project=makwentabot

# VPC networks (if any)
gcloud compute networks list --project=makwentabot
```

**Cost Estimates** (per month, approximate):
- **Cloud Run**: Free tier = 2M requests, 360,000 GB-seconds, 180,000 vCPU-seconds
  - After free tier: ~$0.00002400/GB-second, ~$0.00001800/vCPU-second
- **Secret Manager**: $0.06 per 10k accesses + $0.003/secret version/month
- **Container Registry**: $0.026/GB storage
- **Cloud Logging**: Free 50GB, then $0.50/GB
- **Network Egress**: $0.085-0.23/GB (varies by destination)

---

## Audit Report Format

When running this skill, generate a report like:

```
📊 BILLING AUDIT REPORT - [DATE]
═══════════════════════════════════════

1️⃣ BILLING OVERVIEW
   Current Month: $X.XX (Est.)
   Last Month: $Y.YY
   Change: +/- Z%

   Top Services:
   • Cloud Run: $A.AA
   • Secret Manager: $B.BB
   • Container Registry: $C.CC

2️⃣ HIDDEN CHARGES DETECTED
   ⚠️ [Issue]: [Description]
   💰 Impact: [Cost estimate]
   ✅ Fix: [Recommendation]

3️⃣ SUBSCRIPTIONS
   GCP Services:
   • Cloud Run (makwenta-bot-service)
   • Secret Manager (3 secrets)
   • Container Registry (gcr.io/makwentabot)

   External Services:
   • Supabase: [Plan] - $X/month
   • OpenAI API: Pay-as-you-go - $Y last month

4️⃣ COST OPTIMIZATION
   💡 Quick Wins:
   • Delete N old container images → Save $X/month
   • Remove M unused revisions → Save $Y/month
   • Review log retention → Save $Z/month

   📈 Monitoring:
   • Budget alerts: [Configured/Not configured]
   • Spending trend: [Stable/Increasing/Decreasing]

5️⃣ RESOURCE INVENTORY
   • Cloud Run services: N
   • Container images: M
   • Secrets: P
   • Old revisions: Q
```

---

## Advanced Checks

### Monitor OpenAI Token Usage
- Track token usage over time
- Calculate cost per user interaction
- Recommend switching models if costs are high (gpt-4o-mini → gpt-3.5-turbo)

### Database Query Efficiency
- Check Supabase dashboard for slow queries
- Unused indexes consuming storage
- Connection pool limits

### Webhook Efficiency
- Check Telegram webhook response times
- Excessive retries may cause duplicate charges

### Container Image Size
- Larger images = longer pull times = higher egress costs
- Recommend multi-stage Docker builds

---

## Validation Criteria

✅ **Audit is complete when**:
1. All enabled GCP services identified and costs estimated
2. Hidden charges detected and quantified
3. All subscriptions listed with renewal dates
4. At least 3 cost optimization recommendations provided
5. Resource inventory complete
6. Budget alert status checked

❌ **Red flags to report immediately**:
- "Always allocated" CPU on Cloud Run
- Budget exceeded or no budget alerts configured
- >50 old container images in GCR
- >20 old Cloud Run revisions
- OpenAI costs exceeding $50/month (may indicate abuse)
- Supabase approaching free tier limits

---

## Usage Instructions

**Invoke this skill when**:
- User asks "check my billing" or "audit costs"
- Monthly billing review
- Before major feature deployments
- After detecting unexpected charges
- Quarterly cost optimization review

**Output**:
- Comprehensive billing audit report
- Prioritized action items
- Cost-saving recommendations with estimated impact
- Timeline for next audit (recommend monthly)
