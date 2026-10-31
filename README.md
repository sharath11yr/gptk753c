# GetYr_CSE – CS course series automation

A copy of the story-channel automation, set up for the electronics channel. Every hour,
cron-job.org starts **Actions → Daily video**. A new episode is made about every 6 hours (4 a day),
and 2 are published a day (12:00 and 18:00 India time), each with a vertical Short.

1. **Lesson:** the next lesson of a course in `pipeline/courses.py` (Python, Java, Git, DBMS, OS,
   CN, OOP, ML, Gen AI, DSA), beginner to advanced, with courses taking turns
   (`state/course_progress.json`).
2. **Script:** an in-depth lesson (intuition, concept, examples, internals, mistakes) for students
   (NVIDIA API), then a strict CS-professor review.
3. **Video:** a NotebookLM cinematic video in an educational animation style, added automatically
   to its course playlist. The website
   removes the watermark, then the intro, outro and the corner text GetYr_CSE are added.
4. **Upload:** an SEO title and description, the title-screen thumbnail, and scheduling.
   NotebookLM's own Short (or a clip cut from the episode) is uploaded with it.

Setup and fixes: see `MAINTENANCE.md`. Content modes: `CONTENT_MODE` = `courses` (default), `electronics`,
`stories` or `series`.
