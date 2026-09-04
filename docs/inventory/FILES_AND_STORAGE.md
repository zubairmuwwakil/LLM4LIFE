# Files & Storage Inventory

**Status:** Provisional / subject to change  
**Inventory date:** 2026-09-02

This records the current files/storage setup and the likely production-grade direction. Final implementation decisions should be made after the full software-stack inventory is complete.

## Current usage

| System | Current role | Provisional direction |
|---|---|---|
| Google Drive | General cloud file storage; native home for Google Docs, Sheets, and Slides | Preferred candidate for canonical personal cloud document/file storage |
| Google Docs / Sheets / Slides | Cloud-native document, spreadsheet, and presentation authoring inside Google Drive | Keep as document types/interfaces within Google Drive, not separate storage systems |
| OneDrive | Cloud storage and synchronization for local Mac folders; overlaps with Google Drive | Keep only where Microsoft-specific value, sharing, or compatibility justifies it; otherwise reduce duplicate storage |
| Local Mac folders | Working filesystem; currently synchronized/uploaded through Google Drive and/or OneDrive | Treat as local working/cache layer rather than independent canonical storage where practical |
| External hard drive / Time Machine | Mac backup and recovery | Keep. Backup is a separate responsibility from cloud storage and should not be treated as a user-facing source of truth |

## Main architectural issue

The current setup has overlapping cloud ownership between **Google Drive and OneDrive**. A production-grade personal system should avoid routinely maintaining the same durable file in multiple cloud hierarchies unless one copy is explicitly a backup or replication target.

## Provisional recommendation

Use **Google Drive as the default canonical personal file/document store**, mainly because the broader LLM4LIFE stack is already moving toward Google Calendar, Google Tasks, Gmail, and Google-native documents, and Google Drive is a strong AI/integration surface.

Use OneDrive only for a clearly defined purpose, such as:

- Microsoft/Office-specific workflows;
- collaboration with people or organizations that require OneDrive/SharePoint;
- a deliberate secondary replication strategy if implemented and monitored as backup rather than as a second editable source of truth.

Do not keep Google Drive and OneDrive as two equal, manually managed homes for the same class of personal files.

## Target ownership model

```text
                User / apps / LLM4LIFE
                         |
                         v
                  Google Drive
          canonical personal file store
             /          |          \
          Docs        Sheets       Files/PDFs

Local Mac filesystem -> working/synced access

Time Machine -> independent device backup/recovery

OneDrive -> exception path only when Microsoft-specific value exists
```

## Important distinction

**Cloud synchronization is not backup.** Accidental deletion, corruption, or unwanted changes can synchronize too. Time Machine therefore remains useful even if Google Drive becomes canonical.

## Open questions before final implementation

1. Identify what currently lives only in OneDrive versus only in Google Drive.
2. Determine whether any Microsoft Office / SharePoint workflows require OneDrive long-term.
3. Decide the canonical folder taxonomy for durable personal documents.
4. Define where sensitive documents belong and whether encryption/access-control requirements differ from ordinary files.
5. Decide whether an additional off-site/versioned backup is worthwhile beyond Google Drive + Time Machine.

## Implementation commitment

After the complete software-stack inventory session, implement the agreed long-term storage structure rather than leaving this as documentation-only guidance. Migration should be staged and deduplicated carefully to avoid data loss or link breakage.
