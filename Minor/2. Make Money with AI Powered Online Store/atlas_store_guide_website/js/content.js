/*
 * Guide content: edit this file to change what the site says.
 * No build step. The page reads window.GUIDE when it loads.
 *
 * Chapter fields
 *   id     number, 1..N in order, no gaps
 *   title  full chapter title
 *   short  short label (keep it filled)
 *   type   "action"   -> steps have checkboxes and count toward progress
 *          "overview" -> plain points, no checkboxes, not counted
 *   steps  array of strings, or objects { t, sub, fix }
 *            t    the step text
 *            sub  optional array of strings shown as a bullet list under the step
 *            fix  optional troubleshooting text, shown as a highlighted "Fix"
 *
 * Inline formatting inside any text: **bold** and ~~strikethrough~~
 *
 * Progress is saved per chapter id + step position. When you edit steps after
 * people have started, add new steps at the END of a chapter or raise
 * GUIDE.version so old saved progress is ignored.
 */
window.GUIDE = {
  version: 1,
  title: "Shopify + Atlas: AI store guide",
  chapters: [
    {
      id: 1,
      title: "Trailer: an online store in 10 minutes",
      short: "Trailer",
      type: "overview",
      steps: [
        "Online store in 10 min with just one Amazon link (~~coding~~, ~~designer~~, ~~product photos~~)",
        "Product descriptions written by AI, customer FAQs generated automatically",
        "AI-generated product photos",
        "Bundle deals, upsells, payment options and launch, all in one click",
        "Real store (~~demo~~) that can start making money today",
        "Shopify setup, Atlas AI builder, theme customization"
      ]
    },
    {
      id: 2,
      title: "Your Shopify store starts here",
      short: "Shopify setup",
      type: "action",
      steps: [
        "Open the Shopify landing page and log in using your name and password",
        "Choose the Free Trial offer (if you want the store to run longer, subscribe using UPI or credit card)",
        "Answer Shopify's custom question set",
        "Open Atlas (theme builder) for free and install it on your local machine",
        "The installed Atlas takes you to Shopify",
        "On the Shopify main page we will build our store and set the theme"
      ]
    },
    {
      id: 3,
      title: "Zero skills, no problem: AI does it all",
      short: "The plan",
      type: "overview",
      steps: [
        "Platform? Design? Product photos? Descriptions? Too much confusion. AI can handle all of it",
        "Product → Store (using Shopify and the AI tool Atlas)",
        "Descriptions, FAQs and shipping details, all by AI",
        "Set up the Shopify account → install Atlas → let AI create our store → customize theme and product pages → AI professional product photos → bundle deals and go live",
        "A freelancer, a school student, anyone who has never worked with AI can make an online store easily"
      ]
    },
    {
      id: 4,
      title: "One click and AI builds everything",
      short: "Build the store",
      type: "action",
      steps: [
        "Atlas is attached inside Shopify → Atlas Dashboard",
        "Atlas → Bundle deals, AI photos, Build AI store",
        "Build AI Store → fill in the details and choose the default Atlas template",
        "Link options → products already added in Shopify and/or listings from other product websites",
        "Amazon → **Carpet** → copy the link",
        "Atlas → Amazon product link option",
        "Everything gets created on its own → Atlas crafting a premium store",
        "AI does market research without asking us for details"
      ]
    },
    {
      id: 5,
      title: "AI wrote the entire product page",
      short: "Product page",
      type: "action",
      steps: [
        "Store created → select images (at least 4), pulled directly from the Amazon link",
        {
          t: "Customize the product page",
          sub: [
            "Price",
            "Title",
            "Key qualities of the product highlighted",
            "Quantity selector",
            "Add to Cart button",
            "Customer reviews",
            "Multiple payment options",
            "AI-written description",
            "Processing and shipping details",
            "\"Transform your home\" section with the percentage effect already populated",
            "Shop Now button",
            "Support info"
          ]
        },
        "Everything is editable and customizable (even the colour scheme, homepage text, product qualities, FAQ, media sections, persuasion and benefits)",
        "Launch your store → buy a plan before launching"
      ]
    },
    {
      id: 6,
      title: "Which plan should you buy? Don't waste money",
      short: "Choose a plan",
      type: "action",
      steps: [
        "The free plan we are already using will not show in the list",
        "The plan that we purchase will show as the current plan",
        "To publish the store, we need at least the Starter or the Growth plan",
        "Details about the Starter plan and the Growth plan",
        "Select the plan, add billing details, wait for the payment to go through",
        "After completion, come back and publish the store",
        "Click Publish to make the theme go live"
      ]
    },
    {
      id: 7,
      title: "Change anything in your store: here's how",
      short: "Edit the theme",
      type: "action",
      steps: [
        "After publishing the theme → (right side) Edit Theme button",
        "Front page → the first thing a user sees when visiting the store (customizable)",
        "Open the Product page → this is the prime focus",
        "Editing suggestions and tools are on the left side (anything and everything set up before can be easily modified)",
        "Click any icon on the left and its options generate instantly",
        "Save and move on"
      ]
    },
    {
      id: 8,
      title: "No photoshoot needed: AI creates product photos",
      short: "AI photos",
      type: "action",
      steps: [
        "On the left pane, below AI Store Builder, select AI Product Photos",
        "Provide a reference link and describe the product image (key highlight)",
        "Generate prompt → Generate image → Save image",
        "AI Store → Add product page (new product)"
      ]
    },
    {
      id: 9,
      title: "This one trick doubles your sales instantly",
      short: "Bundle deals",
      type: "action",
      steps: [
        "AI Store → Bundle deals → Create Bundle",
        "Select a template → select a colour → Proceed",
        "Bundles = offers for customers (highlight deals)",
        "Edit all details as per your offers → Publish Bundle",
        {
          t: "If another bundle is already applied to **All products**, you cannot apply a bundle to all products again.",
          fix: "Select a specific collection or a specific product."
        }
      ]
    },
    {
      id: 10,
      title: "Your store is live: see the final result",
      short: "Go live",
      type: "action",
      steps: [
        "Activate Bundle → Atlas Bundler",
        "New section before the cart → Apps → Atlas Bundler",
        "Instead of adding items manually, customers can click on the bundle and click Add to Cart (key functionality)",
        "Save and Exit",
        "Online Store → View your store"
      ]
    },
    {
      id: 11,
      title: "What's stopping you from starting today?",
      short: "Start today",
      type: "overview",
      steps: [
        "A fully functional online store just by using AI",
        "Useful for someone waiting to build their online business"
      ]
    }
  ]
};
