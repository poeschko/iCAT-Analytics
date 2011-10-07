/*
ICDexplorer

(c) 2011 Jan Poeschko
jan@poeschko.com
*/

var SEARCH_DEFAULT = "Search";
//alert(SEARCH_DEFAULT);

function activateSearch() {
	var searchField = $('#searchField');
  if (searchField.val() == SEARCH_DEFAULT) {
  	searchField.val('');
  	searchField.removeClass('empty').addClass('filled');
  }
}

$(document).ready(function() {
	var searchField = $('#searchField');
  if (searchField.val() == SEARCH_DEFAULT) {
  	searchField.removeClass('filled').addClass('empty');
  } else
  	searchField.removeClass('empty').addClass('filled');
  
  searchField.bind('click', activateSearch);
  searchField.bind('mouseup', function() {
    if (searchField.val() == SEARCH_DEFAULT)
    	searchField.removeClass('empty').addClass('filled');
  });
  searchField.bind('blur', function() {
    if (searchField.val() == '' || searchField.val() == SEARCH_DEFAULT) {
    	searchField.val(SEARCH_DEFAULT);
    	searchField.removeClass('filled').addClass('empty');
    }
  });
});