# From one accepted video to a series

Make a template only when the second and third videos came out the same way by hand.
Make more complex only the part that already limits quality or speed.

## Separate design from content

| Fixed (the template) | Varies (the input) |
| --- | --- |
| layout per format, zones, fonts, colours | headline, numbers, quotes |
| caption style and limits | media files, logo variant |
| scene order and timing rules | voice recording, music choice |
| transitions and motion rules | language |

For every input field, write down:
its type, the allowed length (in characters, per language),
whether it is optional, and the fallback layout when it is long or missing.
A good template constrains the right places —
headline length, number of points, caption size, number of scenes —
so the series stays recognisable.

## Test before the first real batch

1. A short text.
2. A long text in the longest language of the series (Russian runs longer than English).
3. A missing optional asset.

Validate the input before rendering; a render is the most expensive way to find a too-long headline.
Give the agent two or three accepted examples and say what is good in each:
pace, composition, how much text a frame can hold.

## Running a batch

- One input file or one data row is one job.
- Every job carries a stable name and the template version.
- Running a job again does not create duplicates.
- Failed jobs go to a separate list with their error.
- A person watches each video before it is published (`acceptance-checklist.md`).

## Engines

- HyperFrames compositions take variables, and Remotion compositions take props;
  their skills own how (`hyperframes-core`, `remotion-best-practices`).
- A video service driven through an API or MCP must return checkable results:
  a job ID, a status, a file path and an error report.
  A message that says "done" is not an export; check which operations the connection really allows first.
