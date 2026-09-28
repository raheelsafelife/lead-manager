// Defense in depth behind the domain-specific Nginx policy.
export function searchPrivacy(req, res, next) {
  if (req.hostname.toLowerCase() === "ccpleads.safelifehomehealth.com") {
    res.setHeader("X-Robots-Tag", "noindex, nofollow, noarchive");
  }
  next();
}
