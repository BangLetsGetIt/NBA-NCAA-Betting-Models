# 💰 RevenueCat Integration Guide

You already have your RevenueCat API key - great! Here's how to integrate it into your app.

---

## 📋 Step-by-Step Integration

### Step 1: Add RevenueCat Package to Xcode

1. Open your project in Xcode
2. Click **File → Add Package Dependencies**
3. Paste this URL: `https://github.com/RevenueCat/purchases-ios.git`
4. Version: **Up to Next Major** (latest stable)
5. Click **Add Package**
6. Select **RevenueCat** and click **Add Package**

### Step 2: Update Config.swift with Your API Key

1. Open `Config.swift`
2. Find this line:
   ```swift
   static let revenueCatAPIKey = "YOUR_REVENUECAT_API_KEY_HERE"
   ```
3. Replace with your actual API key:
   ```swift
   static let revenueCatAPIKey = "appl_xxxxxxxxxxxxxxxxx"
   ```
   **IMPORTANT**: Your API key should start with `appl_` for iOS apps

### Step 3: Uncomment RevenueCat Import

1. Open `CourtSideApp.swift`
2. Find the commented import at the top:
   ```swift
   // Uncomment this when you add RevenueCat package:
   // import RevenueCat
   ```
3. Uncomment it:
   ```swift
   import RevenueCat
   ```

### Step 4: Activate RevenueCat Code

**In `CourtSideApp.swift`:**

1. Find the `configureRevenueCat()` function (around line 181)
2. **Remove** the `/*` and `*/` comment markers
3. The code should look like this:
   ```swift
   private func configureRevenueCat() {
       Purchases.logLevel = AppConfig.enableDebugLogging ? .debug : .info
       Purchases.configure(withAPIKey: AppConfig.revenueCatAPIKey)

       if AppConfig.enableDebugLogging {
           print("✅ RevenueCat configured with API key")
       }
   }
   ```

4. Do the same for `checkSubscriptionStatus()` function (around line 193)
5. Do the same for `restorePurchases()` function (around line 216)

**In `PaywallView.swift`:**

1. Find the `purchase()` function (around line 177)
2. **Remove** the `/*` and `*/` comment markers around the RevenueCat code
3. **Delete** or comment out the "TEMPORARY" simulation code
4. Do the same for `restorePurchases()` function (around line 240)

### Step 5: Set Up Products in RevenueCat Dashboard

1. Go to [RevenueCat Dashboard](https://app.revenuecat.com/)
2. Select your app
3. Navigate to **Products** tab
4. Create an **Entitlement** called `pro`
5. Create two **Products**:
   - **Monthly**: `pro_monthly` → $9.99/month
   - **Annual**: `pro_annual` → $79.99/year
6. Attach both products to the `pro` entitlement

### Step 6: Set Up Products in App Store Connect

1. Go to [App Store Connect](https://appstoreconnect.apple.com/)
2. My Apps → Your App → Features → In-App Purchases
3. Click the **+** button to create new products
4. Create two **Auto-Renewable Subscriptions**:

**Monthly Subscription:**
- **Reference Name**: Pro Monthly
- **Product ID**: `pro_monthly` (must match RevenueCat!)
- **Subscription Group**: Create new group "Pro Subscriptions"
- **Price**: $9.99/month
- **Review Notes**: Premium NBA analytics subscription

**Annual Subscription:**
- **Reference Name**: Pro Annual
- **Product ID**: `pro_annual` (must match RevenueCat!)
- **Subscription Group**: Same group as monthly
- **Price**: $79.99/year
- **Review Notes**: Premium NBA analytics subscription (annual)

5. Submit both for review (they need to be "Ready to Submit" status)

### Step 7: Link App Store Connect to RevenueCat

1. Back in RevenueCat Dashboard
2. Go to **Project Settings** → **App Store Connect**
3. Follow the setup wizard to connect your App Store Connect account
4. RevenueCat will automatically sync your products

---

## 🧪 Testing Subscriptions

### Test on Simulator (Sandbox Mode)

1. RevenueCat automatically uses StoreKit sandbox for testing
2. Run your app in simulator
3. Try to subscribe - you won't be charged
4. Apple's sandbox allows you to test purchase flows

### Create Sandbox Test Accounts

1. Go to [App Store Connect](https://appstoreconnect.apple.com/)
2. Users and Access → Sandbox Testers
3. Click **+** to create test accounts
4. Use these accounts to test purchases on real devices

### Enable StoreKit Testing in Xcode

1. In Xcode: **Product → Scheme → Edit Scheme**
2. **Run → Options → StoreKit Configuration**
3. Create a new StoreKit configuration file if needed
4. This allows testing without real App Store connection

---

## 🐛 Debugging

### Check RevenueCat is Configured

When you run the app, look in Xcode console for:
```
✅ RevenueCat configured with API key
✅ Subscription status: Active/Inactive
```

### Enable Debug Logging

In `Config.swift`, set:
```swift
static let enableDebugLogging = true
```

This will show detailed logs from RevenueCat.

### Common Issues

**Issue**: "No packages found"
- **Fix**: Make sure products are created in both RevenueCat AND App Store Connect
- Products must have "Ready to Submit" status in App Store Connect

**Issue**: "Invalid API Key"
- **Fix**: Double-check your API key in `Config.swift`
- Ensure it starts with `appl_` for iOS

**Issue**: Purchases not working on real device
- **Fix**: Make sure you're signed in with a sandbox test account
- Settings → App Store → Sign out → Sign in with sandbox account

**Issue**: "The operation couldn't be completed"
- **Fix**: Products need to be synced from App Store Connect
- Wait 30 minutes after creating products, then try again

---

## ✅ Verification Checklist

Before testing, ensure:
- [ ] RevenueCat package added to Xcode
- [ ] API key added to `Config.swift`
- [ ] All RevenueCat code uncommented in `CourtSideApp.swift`
- [ ] All RevenueCat code uncommented in `PaywallView.swift`
- [ ] `import RevenueCat` added to necessary files
- [ ] Entitlement `pro` created in RevenueCat
- [ ] Products `pro_monthly` and `pro_annual` created in RevenueCat
- [ ] Same products created in App Store Connect with exact same IDs
- [ ] App Store Connect linked to RevenueCat
- [ ] Sandbox test account created

---

## 🚀 Next Steps

Once RevenueCat is fully integrated:
1. Test the purchase flow in simulator
2. Test on real device with sandbox account
3. Verify subscription status updates correctly
4. Test restore purchases functionality
5. Deploy to TestFlight for beta testing

**You're almost there!** This is the final piece to monetize your app.
