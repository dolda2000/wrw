<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en-US">
<head>
${self.htmlhead()}
</head>
<body>
${next.body()}
</body>
</html>

<%def name="htmlhead()">
    <title>${self.title()}</title>
</%def>

<%def name="title()">
    Untitled Page
</%def>
