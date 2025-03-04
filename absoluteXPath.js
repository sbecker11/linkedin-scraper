
function absoluteXPath(element) {
    var comps = [];
    var getPos = function(element) {
        var position = 1, curNode;
        if (element.nodeType == Node.ATTRIBUTE_NODE) {
            return null;
        }
        for (curNode = element.previousSibling; curNode; curNode = curNode.previousSibling) {
            if (curNode.nodeName == element.nodeName) {
                ++position;
            }
        }
        return position;
    };

    if (element instanceof Document) {
        return '/';
    }

    for (; element && !(element instanceof Document); element = element.nodeType == Node.ATTRIBUTE_NODE ? element.ownerElement : element.parentNode) {
        var comp = {};
        switch (element.nodeType) {
            case Node.TEXT_NODE:
                comp.name = 'text()';
                break;
            case Node.ATTRIBUTE_NODE:
                comp.name = '@' + element.nodeName;
                break;
            case Node.PROCESSING_INSTRUCTION_NODE:
                comp.name = 'processing-instruction()';
                break;
            case Node.COMMENT_NODE:
                comp.name = 'comment()';
                break;
            case Node.ELEMENT_NODE:
                comp.name = element.nodeName;
                break;
        }
        comp.position = getPos(element);
        comps.push(comp);
    }

    var xpath = '';
    for (var i = comps.length - 1; i >= 0; i--) {
        var comp = comps[i];
        xpath += '/' + comp.name.toLowerCase();
        if (comp.position !== null) {
            xpath += '[' + comp.position + ']';
        }
    }

    return xpath;
}

