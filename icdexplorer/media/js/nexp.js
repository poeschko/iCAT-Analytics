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
		setElementAttr(this.elementSensitive || this.element, "cursor", properties.cursor);
		setElementAttr(this.elementSensitive || this.element, "href", properties.href);
		if ((typeof this.currentProperties.caption == "undefined") || properties.caption != this.currentProperties.caption) {
			if (this.captionElement)
				this.captionElement.remove();
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
		}
		this.currentProperties = properties;
	}
	
	this.getCaptionPos = function() {
		return null;
	}
	
	this.getDefaultProperties = function() {
		return {};
	}
	
	this.setProperties = function(properties, highlightProperties, secondaryHighlightProperties,
			unhighlightProperties, use) {
		this.properties = properties || {};
		this.properties.fill = this.properties.fill || "black";
		this.properties.fillOpacity = this.properties.fillOpacity || 1;
		this.highlightProperties = highlightProperties || {};
		this.secondaryHighlightProperties = secondaryHighlightProperties || {};
		this.unhighlightProperties = unhighlightProperties || {};
		setDefault(this.properties, this.getDefaultProperties());
		setDefault(this.highlightProperties, this.properties);
		setDefault(this.secondaryHighlightProperties, this.highlightProperties);
		setDefault(this.unhighlightProperties, this.properties);
		if (typeof use == "undefined" || use)
			this.useProperties(this.properties);
	}
	
	this.renderCaption = function() {
		if (this.captionElement) {
			var pos = this.getCaptionPos();
			this.captionElement.attr({x: pos.x, y: pos.y});
		}		
	}

	this.highlight = function() {
		this.useProperties(this.highlightProperties);
	}
	this.secondaryHighlight = function() {
		this.useProperties(this.secondaryHighlightProperties);
	}
	this.unhighlight = function() {
		this.useProperties(this.unhighlightProperties);
	}
	this.resetHighlight = function() {
		this.useProperties(this.properties);
	}
	
	this.onHoverEnter = function() {
	}
	
	this.onHoverLeave = function() {
	}
}

var NODE_ID = 1;

function Node(network, id, pos, properties, highlightProperties, secondaryHighlightProperties,
		unhighlightProperties) {
	this.network = network;
	this.id = id || "node" + (NODE_ID++);
	this.pos = pos;
	this.properties = {};
	this.edges = {};
	this.container = network.nodesSet;
	
	this.setPos = function(pos) {
		this.pos = pos;
		pos = this.getScreenPos(pos);
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
		return new Point(pos.x, pos.y - this.properties.r - this.properties.fontSize / 2 + 1);
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
					if (node.properties.cluster == this.properties.cluster) {
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
				if (node.properties.cluster == this.properties.cluster) {
					node.resetHighlight();
				}
			}
		}
		for (edge in this.edges)
			this.edges[edge].resetHighlight();
	}
	
	this.onClick = function() {
		if (this.currentProperties.href) {
			window.location.href = this.currentProperties.href;
			return;
		}
		if (network.maxSelection > 0) {
			network.toggleSelection(this);
		}
	}
	
	this.setProperties(properties, highlightProperties, secondaryHighlightProperties,
			unhighlightProperties, false);
	
	pos = network.logToScreen(pos.x, pos.y);
	this.element = network.paper.circle(pos.x, pos.y, this.properties.r);
	this.elementSensitive = network.paper.circle(pos.x, pos.y, this.properties.r);
	this.elementSensitive.attr("fill", "white");
	this.elementSensitive.attr("fill-opacity", 0);
	this.elementSensitive.attr("stroke", "none");
	this.elementSensitive.click(this.onClick, this);
	network.nodesSet.push(this.element);
	network.nodesSensitiveSet.push(this.elementSensitive);
	
	this.useProperties(this.properties);
	
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

function Edge(network, from, to, properties, highlightProperties, secondaryHighlightProperties,
		unhighlightProperties) {
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
		return "M" + from.x + " " + from.y + "L" + to.x + " " + to.y;
	}
	
	this.render = function() {
		var path = getPath();
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
			fill: "none",
			stroke: "#666",
			strokeWidth: 1,
			strokeOpacity: 0.5,
			fontColor: "black",
			fontSize: 12,
			cursor: "default"
		}
	}
	
	this.setProperties(properties, highlightProperties, secondaryHighlightProperties, unhighlightProperties);
	
	this.remove = function() {
		delete this.from.edges[this.to.id];
		delete this.to.edges[this.from.id];
		this.element.remove();
		if (this.captionElement)
			this.captionElement.remove();
		delete this.network.edges[this.id];
	}
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
	
	this.maxSelection = this.options.maxSelection || 0; 

	this.center = this.options.center ? new Point(this.options.center[0], this.options.center[1]) : new Point(0, 0);
	this.zoom = typeof this.options.zoom == "undefined" ? 1 : this.options.zoom;
	
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
	
	/// insert pseudo elements to allow arrangement with respect to sets independent of other deleted elements in them
	this.nodesSet.push(this.paper.rect(0, 0, 0, 0));
	this.captionSet.push(this.paper.rect(0, 0, 0, 0));
	this.nodesSensitiveSet.push(this.paper.rect(0, 0, 0, 0));
	
	this.nodes = {};
	this.edges = {};
	
	this.selection = [];
	
	this.loading = false;
	this.loadingDelayed = false;
	this.scrolling = false;
	
	var that = this;
	
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
	
	this.toggleSelection = function(node) {
		var existing = this.selection.indexOf(node);
		//if (existing > -1)
			
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
	
	this.refresh = function() {
		this.loading = true;
		var delNodes = new clone(this.nodes);
		var delEdges = new clone(this.edges);
		var newNodes = [];
		var newEdges = [];
		var min = this.screenToLog(0, 0);
		var max = this.screenToLog(this.screenWidth, this.screenHeight);
		this.triggerCallbacked("view", [min.x, max.x, min.y, max.y, newNodes, newEdges], function() {
			for (nodeData in newNodes) {
				nodeData = newNodes[nodeData];
				var id = nodeData.shift();
				var x = nodeData.shift();
				var y = nodeData.shift();
				var properties = nodeData.shift();
				var highlightProperties = nodeData.shift();
				var secondaryHighlightProperties = nodeData.shift();
				var unhighlightProperties = nodeData.shift();
				var existing = this.nodes[id];
				if (existing) {
					existing.setProperties(properties, highlightProperties, secondaryHighlightProperties, unhighlightProperties);
					existing.setPos(new Point(x, y));
					delete delNodes[id];
				} else {
					this.nodes[id] = new Node(this, id, new Point(x, y), properties,
							highlightProperties, secondaryHighlightProperties, unhighlightProperties);
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
				var highlightProperties = edgeData.shift();
				var secondaryHighlightProperties = edgeData.shift();
				from = this.nodes[from];
				to = this.nodes[to];
				var id = Edge.id(from, to);
				var existing = this.edges[id];
				if (existing) {
					existing.setProperties(properties, highlightProperties, secondaryHighlightProperties);
					existing.render();
					delete delEdges[id];
				} else {
					this.edges[id] = new Edge(this, from, to, properties, highlightProperties,
							secondaryHighlightProperties);
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
		});
	}
	
	var lastDx = 0;
	var lastDy = 0;
	var moved = false;
	this.background.drag(function(dx, dy) {
		if (dx != 0 ||dy != 0)
			moved = true;
		dx -= lastDx;
		dy -= lastDy;
		lastDx += dx;
		lastDy += dy;
		that.contentSet.translate(dx, dy);
		var newCenter = that.screenToLog(that.screenWidth / 2 - dx, that.screenHeight / 2 - dy);
		that.center = newCenter;
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
	}
	
	if (this.options.showNavigationControls) {
		createNavControl(NAVCTRL_POS, "+", function() {
			that.doZoom(2, new Point(that.screenWidth / 2, that.screenHeight / 2));
		});
		createNavControl(NAVCTRL_POS + NAVCTRL_SIZE + NAVCTRL_D, "·​", function() {
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
}

Network.prototype = new Observable();
