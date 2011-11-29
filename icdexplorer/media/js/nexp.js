/*
nexp

(c) 2011 Jan Poeschko
jan@poeschko.com
*/

function clone(object) {
	for (attr in object)
		this[attr] = object[attr];
}

function setDefault(dict, defaults) {
	for (key in defaults)
		if (typeof dict[key] == 'undefined')
			dict[key] = defaults[key];
	return dict;
}

function toggleElement(array, item, max) {
	var existing = array.indexOf(item);
	if (existing >= 0) {
		array.splice(existing, 1);
	} else {
		array.push(item);
		if (array.length > max)
			array.splice(0, array.length - max);
	}
}

function Observable() {
	this.observers = {};
	
	this.bind = function(signal, callback) {
		if (!this.observers[signal])
			this.observers[signal] = [];
		this.observers[signal].push(callback);
	}
	
	this.triggerCallbacked = function(signal, args, callback) {
		var observerIndex = 0;
		var that = this;
		function callObserver() {
			if (that.observers[signal] && observerIndex < that.observers[signal].length) {
				var observer = that.observers[signal][observerIndex++];
				observer.apply(that, args);
			} else
				callback.apply(that, []);
		}
		args = args.concat([callObserver]);
		callObserver();
	}
	
	this.trigger = function(signal, args) {
		for (observerIndex in this.observers[signal]) {
			var observer = this.observers[signal][observerIndex];
			observer.apply(this, args || []);
		}
	}
}

function Point(x, y) {
	this.x = x;
	this.y = y;
	
	this.toString = function() {
		return "(" + this.x + "," + this.y + ")";
	}
	
	this.add = function(other) {
		return new Point(this.x + other.x, this.y + other.y);
	}
	
	this.sub = function(other) {
		return new Point(this.x - other.x, this.y - other.y);
	}
	
	this.mul = function(scalar) {
		return new Point(this.x * scalar, this.y * scalar);
	}
	
	this.abs = function() {
		return Math.sqrt(Math.pow(this.x, 2) + Math.pow(this.y, 2));
	}
	
	this.norm = function() {
		var a = this.abs();
		if (a > 0)
			return new Point(this.x / a, this.y / a);
		return this;
	}
}

function Rect(xmin, xmax, ymin, ymax) {
	this.xmin = xmin;
	this.xmax = xmax;
	this.ymin = ymin;
	this.ymax = ymax;
}

function Highlightable() {
	this.network = null;
	this.container = null;
	this.currentProperties = {};
	this.captionElement = null;
	
	this.highlighted = false;
	this.secondaryHighlighted = false;
	this.unhighlighted = false;
	this.selected = false;
	
	this.getCurrentProperties = function() {
		if (this.selected)
			return this.properties.selected;
		if (this.highlighted)
			return this.properties.highlight;
		if (this.secondaryHighlighted)
			return this.properties.secondaryHighlight;
		if (this.unhighlighted)
			return this.properties.unhighlight;
		return this.properties.normal;
	}
	
	this.useProperties = function(properties) {
		var that = this;
		function setElementAttr(element, attr, value) {
			if (typeof value != "undefined")
				element.attr(attr, value);
		}
		function setAttr(attr, value) {
			if (typeof value != "undefined")
				that.element.attr(attr, value);
		}
		function setCaptionAttr(attr, value) {
			if (typeof value != "undefined")
				that.captionElement.attr(attr, value);
		}
		setAttr("r", properties.r);
		if (this.elementSensitive)
			setElementAttr(this.elementSensitive, "r", properties.r);
		setAttr("fill", properties.fill);
		setAttr("fill-opacity", properties.fillOpacity);
		setAttr("stroke", properties.stroke);
		setAttr("stroke-width", properties.strokeWidth);
		setAttr("stroke-opacity", properties.strokeOpacity);
		setAttr("arrow-start", properties.direction == '<' || properties.direction == '=' ? 'classic-wide-long' : 'none');
		setAttr("arrow-end", properties.direction == '>' || properties.direction == '=' ? 'classic-wide-long' : 'none');
		setElementAttr(this.elementSensitive || this.element, "cursor", properties.cursor);
		setElementAttr(this.elementSensitive || this.element, "href", properties.href);
		if ((typeof this.currentProperties.caption == "undefined") || properties.caption != this.currentProperties.caption) {
			if (this.captionElement) {
				this.captionElement.remove();
				this.captionElement = null;
			}
			if (properties.caption) {
				var pos = this.getCaptionPos();
				this.captionElement = this.network.paper.text(pos.x, pos.y, properties.caption);
				this.network.captionSet.push(this.captionElement);
				this.captionElement.insertBefore(this.network.nodesSet);
				if (this.network.options.highlightHover) {
					this.captionElement.hover(this.onHoverEnter, this.onHoverLeave, this, this);
				}
				this.captionElement.click(this.onClick, this);
			}
		}
		if (this.captionElement) {
			setCaptionAttr("fill", properties.fontColor);
			setCaptionAttr("fill-opacity", properties.fillOpacity);
			setCaptionAttr("href", properties.href);
			setCaptionAttr("font-size", properties.fontSize);
			setCaptionAttr("cursor", properties.cursor);
		}
		this.currentProperties = properties;
	}
	
	this.getCaptionPos = function() {
		return null;
	}
	
	this.getDefaultProperties = function() {
		return {};
	}
	
	this.setProperties = function(properties, use) {
		this.properties = {
			normal: properties.normal || {},
			highlight: properties.highlight || {},
			secondaryHighlight: properties.secondaryHighlight || {},
			unhighlight: properties.unhighlight || {},
			selected: properties.selected || {}
		};
		this.properties.normal.fill = this.properties.normal.fill || "black";
		this.properties.normal.fillOpacity = this.properties.fillOpacity || 1;
		setDefault(this.properties.normal, this.getDefaultProperties());
		setDefault(this.properties.highlight, this.properties.normal);
		setDefault(this.properties.secondaryHighlight, this.properties.highlight);
		setDefault(this.properties.unhighlight, this.properties.normal);
		setDefault(this.properties.selected, this.properties.highlight);
		if (typeof use == "undefined" || use)
			this.useProperties(this.selected ? this.properties.selected : this.properties.normal);
	}
	
	this.renderCaption = function() {
		if (this.captionElement) {
			var pos = this.getCaptionPos();
			this.captionElement.transform("");
			this.captionElement.attr({x: pos.x, y: pos.y});
		}		
	}
	
	this.refreshProperties = function() {
		this.useProperties(this.getCurrentProperties());
	}

	this.highlight = function() {
		this.highlighted = true;
		this.refreshProperties();
	}
	this.secondaryHighlight = function() {
		this.secondaryHighlighted = true;
		this.refreshProperties();
	}
	this.unhighlight = function() {
		this.unhighlighted = true;
		this.refreshProperties();
	}
	this.resetHighlight = function() {
		this.highlighted = false;
		this.secondaryHighlighted = false;
		this.refreshProperties();
	}
	
	this.select = function() {
		this.selected = true;
		this.refreshProperties();
	}
	this.unselect = function() {
		this.selected = false;
		this.refreshProperties();
	}
	
	this.onHoverEnter = function() {
	}
	
	this.onHoverLeave = function() {
	}
}

var NODE_ID = 1;

function Node(network, id, pos, properties) {
	this.network = network;
	this.id = id || "node" + (NODE_ID++);
	this.pos = pos;
	this.properties = {};
	this.edges = {};
	this.container = network.nodesSet;
	
	this.setPos = function(pos) {
		this.pos = pos;
		pos = this.getScreenPos(pos);
		this.element.transform("");
		this.elementSensitive.transform("");
		this.element.attr({cx: pos.x, cy: pos.y});
		this.elementSensitive.attr({cx: pos.x, cy: pos.y});
		this.renderCaption();
	}
	
	this.getScreenPos = function() {
		return this.network.logToScreen(this.pos);
	}
	
	this.getDefaultProperties = function() {
		return {
			r: 5,
			fill: "#333",
			stroke: "none",
			fontColor: "black",
			fontSize: 12,
			cursor: "pointer"
		}
	}
	
	this.getCaptionPos = function() {
		var pos = this.getScreenPos();
		return new Point(pos.x, pos.y - this.properties.normal.r - this.properties.normal.fontSize / 2 + 1);
	}
	
	this.onHoverEnter = function() {
		if (this.network.scrolling)
			return;
		this.highlight();
		this.element.insertBefore(this.network.nodesSet);
		this.elementSensitive.insertBefore(this.network.nodesSensitiveSet);
		if (this.network.options.highlightNeighbors || this.network.options.highlightCluster) {
			if (this.network.options.highlightNeighbors)
				for (edge in this.edges) {
					this.edges[edge].secondaryHighlight();
					this.network.nodes[edge].secondaryHighlight();
				}
			if (this.network.options.highlightCluster) {
				for (node in this.network.nodes) {
					node = this.network.nodes[node];
					if (node.properties.normal.cluster == this.properties.normal.cluster) {
						node.secondaryHighlight();
					}
				}
			}
		}
	}
	
	this.onHoverLeave = function() {
		if (this.network.scrolling)
			return;
		this.resetHighlight();
		for (node in this.edges)
			this.network.nodes[node].resetHighlight();
		if (this.network.options.highlightCluster) {
			for (node in this.network.nodes) {
				node = this.network.nodes[node];
				if (node.properties.normal.cluster == this.properties.normal.cluster) {
					node.resetHighlight();
				}
			}
		}
		for (edge in this.edges)
			this.edges[edge].resetHighlight();
	}
	
	this.onClick = function(event) {
		if (this.currentProperties.href) {
			window.location.href = this.currentProperties.href;
			return;
		}
		if (network.nodesSelectable) {
			if (event.shiftKey)
				toggleElement(network.nodeSelection, this.id, network.maxNodeSelection);
			else
				network.nodeSelection = [this.id];
			network.refreshSelection();
		}
	}
	
	this.setProperties(properties, false);
	
	pos = network.logToScreen(pos.x, pos.y);
	this.element = network.paper.circle(pos.x, pos.y, this.properties.normal.r);
	this.elementSensitive = network.paper.circle(pos.x, pos.y, this.properties.normal.r);
	this.elementSensitive.attr("fill", "white");
	this.elementSensitive.attr("fill-opacity", 0);
	this.elementSensitive.attr("stroke", "none");
	this.elementSensitive.click(this.onClick, this);
	network.nodesSet.push(this.element);
	network.nodesSensitiveSet.push(this.elementSensitive);
	
	this.refreshProperties();
	
	if (this.network.options.highlightHover) {
		this.elementSensitive.hover(this.onHoverEnter, this.onHoverLeave, this, this);
	}
	
	this.remove = function() {
		this.element.remove();
		this.elementSensitive.remove();
		if (this.captionElement)
			this.captionElement.remove();
		delete this.network.nodes[this.id];
		for (edge in this.edges)
			this.edges[edge].remove();
	}
}

Node.prototype = new Highlightable();

function length(from, to) {
	//return from.add(to.mul(-1)).abs();
	return Math.sqrt(Math.pow(from.x - to.x, 2) + Math.pow(from.y - to.y, 2));
}

function Edge(network, from, to, properties) {
	this.network = network;
	this.id = Edge.id(from, to);
	this.from = from;
	this.to = to;
	
	this.from.edges[this.to.id] = this;
	this.to.edges[this.from.id] = this;
	
	this.container = network.edgesSet;
	
	var that = this;
	
	function getPath() {
		var from = that.from.getScreenPos();
		var to = that.to.getScreenPos();
		var d = to.sub(from).norm();
		var l = length(from, to);
		if (length == 0)
			length = 1;
		from = from.add(d.mul(that.from.currentProperties.r));
		to = to.sub(d.mul(that.to.currentProperties.r));
		return "M" + from.x + " " + from.y + "L" + to.x + " " + to.y;
	}
	
	this.render = function() {
		var path = getPath();
		this.element.transform("");
		this.element.attr("path", path);
		this.renderCaption();
	}
	
	this.getCaptionPos = function() {
		var from = that.from.getScreenPos();
		var to = that.to.getScreenPos();
		return new Point((from.x + to.x) / 2, (from.y + to.y) / 2);
	}
	
	this.element = network.paper.path(getPath());
	network.edgesSet.push(this.element);
	
	this.getDefaultProperties = function() {
		return {
			direction: '-',
			fill: "none",
			stroke: "#666",
			strokeWidth: 1,
			strokeOpacity: 0.5,
			fontColor: "black",
			fontSize: 12,
			cursor: "default"
		}
	}
	
	this.setProperties(properties);
	
	this.remove = function() {
		delete this.from.edges[this.to.id];
		delete this.to.edges[this.from.id];
		this.element.remove();
		if (this.captionElement)
			this.captionElement.remove();
		delete this.network.edges[this.id];
	}
	
	this.onClick = function(event) {
		if (network.edgesSelectable) {
			if (even.shiftKey)
				toggleElement(network.edgeSelection, this.id, network.maxEdgeSelection);
			else
				network.edgeSelection = [this.id];
			network.refreshSelection();
		}
	}
	
	this.element.click(this.onClick, this);
}

Edge.prototype = new Highlightable();

Edge.id = function(from, to) {
	var ids = [from.id, to.id];
	ids.sort();
	return "edge-" + ids[0] + "-" + ids[1];
}

function Network(element, screenWidth, screenHeight, options) {
	this.options = options || {};
	
	this.element = document.getElementById(element);
	this.paper = Raphael(element, screenWidth, screenHeight);
	
	this.screenWidth = screenWidth;
	this.screenHeight = screenHeight;
	this.totalWidth = this.options.totalWidth || screenWidth;
	this.totalHeight = this.options.totalHeight || screenHeight;

	this.center = this.options.center ? new Point(this.options.center[0], this.options.center[1]) : new Point(0, 0);
	this.zoom = typeof this.options.zoom == "undefined" ? 1 : this.options.zoom;
	this.defaultZoom = typeof this.options.defaultZoom == "undefined" ? this.zoom : this.options.defaultZoom;

	this.maxNodeSelection = this.options.maxNodeSelection || (1/0);
	this.nodesSelectable = this.options.nodesSelectable || false;
	this.maxEdgeSelection = this.options.maxEdgeSelection || (1/0);
	this.edgesSelectable = this.options.edgesSelectable || false;
	
	this.background = this.paper.rect(0, 0, screenWidth, screenHeight);
	this.background.attr("fill", "white");
	this.background.attr("fill-opacity", 0);
	this.background.attr("stroke", "none");
	
	this.edgesSet = this.paper.set();
	this.captionSet = this.paper.set();
	this.nodesSet = this.paper.set();
	this.nodesSensitiveSet = this.paper.set();
	this.contentSet = this.paper.set();
	this.contentSet.push(this.edgesSet, this.captionSet, this.nodesSet, this.nodesSensitiveSet);
	
	this.controlSet = this.paper.set();
	
	/// insert pseudo elements to allow arrangement with respect to sets independent of other deleted elements in them
	this.nodesSet.push(this.paper.rect(0, 0, 0, 0));
	this.captionSet.push(this.paper.rect(0, 0, 0, 0));
	this.nodesSensitiveSet.push(this.paper.rect(0, 0, 0, 0));
	this.controlSet.push(this.paper.rect(0, 0, 0, 0));
	
	this.nodes = {};
	this.edges = {};
	
	this.nodeSelection = [];
	this.edgeSelection = [];
	
	this.loading = false;
	this.loadingDelayed = false;
	this.scrolling = false;
	
	var that = this;
	
	this.dataVersion = 0;
	
	this.refreshDelayed = function() {
		if (that.loadingDelayed)
			return;
		that.loadingDelayed = true;
		
		function delayed() {
			if (!that.loading) {
				that.refresh();
				that.loadingDelayed = false;
			} else
				window.setTimeout(delayed, 1000);			
		}
		
		delayed();
	}
	
	var lastNodeSelection = [];
	var lastEdgeSelection = [];
	
	this.refreshSelection = function() {
		$.each(this.nodeSelection, function(index, nodeId) {
			if (that.nodes[nodeId] && lastNodeSelection.indexOf(nodeId) < 0)
				that.nodes[nodeId].select();
		})
		$.each(lastNodeSelection, function(index, nodeId) {
			if (that.nodes[nodeId] && that.nodeSelection.indexOf(nodeId) < 0)
				that.nodes[nodeId].unselect();
		})
		$.each(this.edgeSelection, function(index, edgeId) {
			if (lastEdgeSelection.indexOf(edgeId) < 0)
				that.edges[edgeId].select();
		})
		$.each(lastEdgeSelection, function(index, edgeId) {
			if (that.edgeSelection.indexOf(edgeId) < 0)
				that.edges[edgeId].unselect();
		})
		lastNodeSelection = this.nodeSelection.slice();
		lastEdgeSelection = this.edgeSelection.slice();
		this.refresh(true);
	}
	
	this.setSelection = function(selection) {
		this.nodeSelection = selection.slice();
		this.refreshSelection();
	}
	
	this.getSelection = function() {
		return this.nodeSelection.slice();
	}
	
	this.isNodeSelected = function(id) {
		return this.nodeSelection.indexOf(id) >= 0;
	}
	
	this.isEdgeSelected = function(id) {
		return this.edgeSelection.indexOf(id) >= 0;
	}
	
	this.resize = function(screenWidth, screenHeight) {
		this.screenWidth = screenWidth;
		this.screenHeight = screenHeight;
		this.paper.setSize(screenWidth, screenHeight);
		this.background.attr({width: screenWidth, height: screenHeight});
		this.refreshDelayed();
	}
	
	this.screenToLog = function(x, y) {
		if (typeof y == "undefined") {
			/// single parameter: Point instance
			y = x.y;
			x = x.x;
		}
		return new Point((2 * x - this.screenWidth) / (this.totalWidth * this.zoom) + this.center.x,
				(2 * y - this.screenHeight) / (this.totalHeight * this.zoom) + this.center.y);
	}
	
	this.logToScreen = function(x, y) {
		if (typeof y == "undefined") {
			/// single parameter: Point instance
			y = x.y;
			x = x.x;
		}
		return new Point(this.screenWidth / 2 + (x - this.center.x) * (this.totalWidth * this.zoom) / 2,
				this.screenHeight / 2 + (y - this.center.y) * (this.totalHeight * this.zoom) / 2);
	}
	
	this.scrollTo = function(newCenter) {
		this.center = newCenter;
		this.trigger("navigation");
		this.refresh();
	}
	
	this.scrollIntoView = function(points) {
		if (!points.length)
			return;
		var minx = points[0].x, miny = points[0].y, maxx = points[0].x, maxy = points[0].y;
		$.each(points, function(index, point) {
			if (point.x < minx) minx = point.x;
			if (point.y < miny) miny = point.y;
			if (point.x > maxx) maxx = point.x;
			if (point.y > maxy) maxy = point.y;
		})
		this.center = new Point((minx + maxx) / 2, (miny + maxy) / 2);
		if (minx != maxx || miny != maxy) {
			var maxZoom = Math.pow(2, Math.floor(Math.min(Math.log(this.totalWidth / (maxx - minx)) / Math.LN2,
					Math.log(this.totalHeight / (maxy - miny)) / Math.LN2)));
			if (this.zoom > maxZoom)
				this.zoom = maxZoom;
		}
		this.trigger("navigation");
		this.refresh();
	}
	
	this.doZoom = function(factor, screenFocus) {
		if (this.loading)
			return;
		/// logical focus shall remain at same screen position
		var oldFocus = this.screenToLog(screenFocus);
		this.zoom *= factor;
		var newFocus = this.screenToLog(screenFocus);
		var oldCenter = this.center;
		this.center = new Point(this.center.x - newFocus.x + oldFocus.x,
				this.center.y - newFocus.y + oldFocus.y);
		
		this.trigger("navigation");
		
		this.refresh();
	}
	
	this.building = false;
	
	this.useData = function(newNodes, newEdges, selectionChanged) {
		this.building = true;
		var delNodes = new clone(this.nodes);
		var delEdges = new clone(this.edges);
		for (nodeData in newNodes) {
			nodeData = newNodes[nodeData];
			var id = nodeData.shift();
			var x = nodeData.shift();
			var y = nodeData.shift();
			var properties = nodeData.shift();
			var existing = this.nodes[id];
			if (existing) {
				existing.setProperties(properties);
				existing.setPos(new Point(x, y));
				delete delNodes[id];
			} else {
				this.nodes[id] = new Node(this, id, new Point(x, y), properties);
				if (this.nodeSelection.indexOf(id) >= 0)
					this.nodes[id].select();
			}
		}
		for (delNode in delNodes) {
			delNodes[delNode].remove();
		}
		for (edgeData in newEdges) {
			edgeData = newEdges[edgeData];
			var from = edgeData.shift();
			var to = edgeData.shift();
			var properties = edgeData.shift();
			from = this.nodes[from];
			to = this.nodes[to];
			var id = Edge.id(from, to);
			var existing = this.edges[id];
			if (existing) {
				existing.setProperties(properties);
				existing.render();
				delete delEdges[id];
			} else {
				this.edges[id] = new Edge(this, from, to, properties);
				if (this.edgeSelection.indexOf(id) >= 0)
					this.edges[id].select();
			}
		}
		for (delEdge in delEdges) {
			delEdges[delEdge].remove();
		}
		this.loading = false;
		this.nodesSet.toBack();
		this.background.toBack();
		this.edgesSet.toBack();
		this.captionSet.toFront();
		this.nodesSensitiveSet.toFront();
		this.controlSet.toFront();
		this.building = false;
		if (selectionChanged && this.nodeSelection) {
			var points = [];
			var anyOutside = false;
			$.each(this.nodeSelection, function(index, node) {
				var node = that.nodes[node];
				if (node) {					
					var point = node.pos;
					points.push(point);
					var screen = that.logToScreen(point);
					var tol = 0.1;
					if (screen.x < that.screenWidth * tol || screen.x > that.screenWidth * (1 - tol) ||
							screen.y < that.screenHeight * tol || screen.y > that.screenHeight * (1 - tol))
						anyOutside = true;
				}
			})
			if (anyOutside)
				this.scrollIntoView(points);
		}
	}
	
	this.refresh = function(selectionChanged) {
		this.loading = true;
		var newNodes = [];
		var newEdges = [];
		var min = this.screenToLog(0, 0);
		var max = this.screenToLog(this.screenWidth, this.screenHeight);
		var thisVersion = this.dataVersion + 1;
		this.triggerCallbacked("view", [min.x, max.x, min.y, max.y, this.nodeSelection, this.edgeSelection,
		                                selectionChanged,
		                                newNodes, newEdges], function() {
			function trigger() {
				if (thisVersion < that.dataVersion)
					return;
				window.setTimeout(function() {
					if (that.building)
						trigger();
					else {
						that.dataVersion = thisVersion;
						that.useData(newNodes, newEdges, selectionChanged);
					}
				}, 50);
			}
			trigger();
		});
	}
	
	function scroll(dx, dy, noRefresh) {
		that.contentSet.translate(dx, dy);
		var newCenter = that.screenToLog(that.screenWidth / 2 - dx, that.screenHeight / 2 - dy);
		that.center = newCenter;
		if (!noRefresh) {
			that.trigger("navigation");
			that.refresh();
		}
	}
	
	var lastDx = 0;
	var lastDy = 0;
	var moved = false;
	this.background.drag(function(dx, dy) {
		if (dx != 0 || dy != 0)
			moved = true;
		dx -= lastDx;
		dy -= lastDy;
		lastDx += dx;
		lastDy += dy;
		scroll(dx, dy, true);
	}, function() {
		that.scrolling = true;
		lastDx = 0;
		lastDy = 0;
		moved = false;
	}, function() {
		that.scrolling = false;
		if (moved) {
			that.trigger("navigation");
			that.refresh();
		}
	});
	
	if (this.nodesSelectable || this.edgesSelection) {
		that.background.click(function() {
			if (!moved && (that.nodeSelection.length > 0 || that.edgeSelection.length > 0)) {
				that.nodeSelection = [];
				that.edgeSelection = [];
				that.refreshSelection();
			}
		});
	}
	
	var NAVCTRL_SIZE = 16;
	var NAVCTRL_POS = 8;
	var NAVCTRL_D = 2;
	
	function createNavControl(y, caption, action) {
		var control = that.paper.rect(NAVCTRL_POS, y, NAVCTRL_SIZE, NAVCTRL_SIZE, 4);
		control.attr({fill: that.options.controlColor || "black", stroke: "none", cursor: "pointer"});
		var text = that.paper.text(NAVCTRL_POS + NAVCTRL_SIZE/2, y + NAVCTRL_SIZE/2, caption);
		text.attr({fill: "white", cursor: "pointer"});
		text.attr("font-size", NAVCTRL_SIZE);
		control.click(action);
		text.click(action);
		that.controlSet.push(control);
		that.controlSet.push(text);
	}
	
	if (this.options.showNavigationControls) {
		createNavControl(NAVCTRL_POS, "+", function() {
			that.doZoom(2, new Point(that.screenWidth / 2, that.screenHeight / 2));
		});
		createNavControl(NAVCTRL_POS + NAVCTRL_SIZE + NAVCTRL_D, "·​", function() {
			that.zoom = that.defaultZoom;
			that.scrollTo(new Point(0, 0));
		});
		createNavControl(NAVCTRL_POS + 2 * (NAVCTRL_SIZE + NAVCTRL_D), "-", function() {
			that.doZoom(0.5, new Point(that.screenWidth / 2, that.screenHeight / 2));
		});
	}

  if (this.options.mouseWheelZoom) {
	  function onMouseWheel(event) {
      var wheel = event.wheelDelta? event.wheelDelta / 120 : -(event.detail || 0) / 3;
      var factor = Math.pow(2.0, wheel > 0 ? 1 : -1);
      var mouseX = typeof event.offsetX == "undefined" ? event.layerX : event.offsetX;
      var mouseY = typeof event.offsetY == "undefined" ? event.layerY : event.offsetY;
      that.doZoom(factor, new Point(mouseX, mouseY));
	  }
	  if (!document.getBoxObjectFor && window.mozInnerScreenX == null)
		  this.element.addEventListener('mousewheel', onMouseWheel);
	  else
	  	this.element.addEventListener('DOMMouseScroll', onMouseWheel, false);
  }
  
  $(window).keydown(function(event) {
  	switch (event.which) {
  	case 107:	// +
  	case 187:	// Chrome
  		that.doZoom(2, new Point(that.screenWidth / 2, that.screenHeight / 2));
  		break;
  	case 109: // -
  	case 189:	// Chrome
  		that.doZoom(0.5, new Point(that.screenWidth / 2, that.screenHeight / 2));
  		break;
  	case 38:	// up
  	case 104:	// numpad 8
  		scroll(0, +that.screenHeight / 3);
  		break;
  	case 40:	// down
  	case 98:	// numpad 2
  		scroll(0, -that.screenHeight / 3);
  		break;
  	case 37:	// left
  	case 100:	// numpad 4
  		scroll(+that.screenWidth / 3, 0);
  		break;
  	case 39:	// right
  	case 102:	// numpad 6
  		scroll(-that.screenWidth / 3, 0);
  		break;
  	case 190:	// .
  	case 110: // numpad decimal point
  	case 188:	// Chrome numpad ,
  		that.zoom = that.defaultZoom;
			that.scrollTo(new Point(0, 0));
			break;
  	}
  });
}

Network.prototype = new Observable();
