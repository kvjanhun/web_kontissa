DROP TABLE IF EXISTS sections;

CREATE TABLE section (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    content TEXT NOT NULL
);

INSERT INTO section (slug, title, content) VALUES
('who', 'Who', 'Konsta Janhunen, currently working as an Integration Developer at Digia Finland Oy, also a computer science student at University of Helsinki. My most common nickname throughout the years has been erezac.'),
('what', 'What', '<p>Integrations is all about tying multiple systems together with various technologies. My part involves a lot of trouble tackling and information hunting, SQL queries being an important tool. Transferring data securely is essential and I''ve become well-versed in the practicalities of encryption, for example, with GnuPG.</p><p>On my free-time I tend to mostly stare at screens a bit more. Thankfully, our young flat-coated retriever keeps me active and forces me outside. I''m an avid PC gamer and my favourites include games in several genres from RPGs to FPSes, roguelikes to 4Xes.</p><p>I also like reading about technology and trying new stuff. This site is self-hosted on an Intel NUC running Red Hat Linux. The server is currently used only to host this project and an SSH server for easy access in LAN. DNS server and email-forwarding are provided by Domainhotelli and ImprovMX</p><p>The site is rendered by Flask, served by Gunicorn, powered by MongoDB and containerised with Docker Compose. Changes to GitHub remote are automatically deployed with a webhook.</p>'),
('where', 'Where', 'You can email me to konsta at erez.ac or message me in Telegram. I have a LinkedIn profile but I''m inactive there. I''m currently not looking for a new job.');

