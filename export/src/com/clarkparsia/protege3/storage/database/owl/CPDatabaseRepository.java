package com.clarkparsia.protege3.storage.database.owl;

import java.io.IOException;
import java.io.OutputStream;
import java.net.URI;
import java.net.URISyntaxException;
import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;

import com.clarkparsia.protege3.storage.database.CPDatabaseFrameDb;

import edu.stanford.smi.protege.exception.AmalgamatedLoadException;
import edu.stanford.smi.protege.exception.OntologyLoadException;
import edu.stanford.smi.protege.storage.database.DatabaseFrameDb;
import edu.stanford.smi.protege.storage.database.DatabaseFrameDbFactory;
import edu.stanford.smi.protege.storage.database.DatabaseProperty;
import edu.stanford.smi.protege.storage.database.IdleConnectionNarrowFrameStore;
import edu.stanford.smi.protege.storage.database.ValueCachingNarrowFrameStore;
import edu.stanford.smi.protege.util.Log;
import edu.stanford.smi.protegex.owl.database.DatabaseFactoryUtils;
import edu.stanford.smi.protegex.owl.model.OWLModel;
import edu.stanford.smi.protegex.owl.model.factory.FactoryUtils;
import edu.stanford.smi.protegex.owl.model.triplestore.TripleStore;
import edu.stanford.smi.protegex.owl.model.triplestore.TripleStoreModel;
import edu.stanford.smi.protegex.owl.repository.Repository;

/*
 * TODO - this class should inherit from DatabaseRepository or something.
 *        They are far too similar.
 */

public class CPDatabaseRepository implements Repository {
    private final static Logger log = Log.getLogger(CPDatabaseRepository.class);
    
	private Connection connection;
	private Map<DatabaseProperty, String> fieldMap = new EnumMap<DatabaseProperty, String>(DatabaseProperty.class);
	
	private Map<URI, String> ontologyToTable = new HashMap<URI, String>();
	private Map<String, URI> tableToOntology = new HashMap<String, URI>();
	
	private Set<String> allTables = new HashSet<String>();
	
	public final static String REPOSITORY_DESCRIPTOR_PREFIX = "Clark-Parsia-Database:";
	public final static char SEPARATOR_CHAR = ',';
	
    public static final String SQL_TABLE_TYPE = "TABLE";
    public static final String SQL_VIEW_TYPE  = "VIEW";
    public int SQL_GET_TABLE_TYPES_TABLE_TYPE_COL=1;
    public int SQL_GET_TABLES_TABLENAME_COL=3;
    
    public final static DatabaseProperty[] DATABASE_FIELDS = { 
        DatabaseProperty.DRIVER_PROPERTY,
        DatabaseProperty.URL_PROPERTY,
        DatabaseProperty.USERNAME_PROPERTY,
        DatabaseProperty.PASSWORD_PROPERTY
    };
    public static int getDBPropertyIndex(DatabaseProperty property) {
        int i = 0;
        for (DatabaseProperty other : DATABASE_FIELDS) {
            if (property == other) {
                return i;
            }
            i++;
        }
        throw  new IllegalArgumentException("Invalid property");
    }
	
	static public List<String> parse(String repositoryDescriptor) {
		List<String> fields = new ArrayList<String>();
		int start = REPOSITORY_DESCRIPTOR_PREFIX.length();
		while (true) {
			int end = repositoryDescriptor.indexOf(SEPARATOR_CHAR, start);
			if (end < 0) {
				fields.add(repositoryDescriptor.substring(start));
				return fields;
			}
			fields.add(repositoryDescriptor.substring(start, end));
			start = end + 1;
		}
	}
	
	public CPDatabaseRepository(String driver,
	                          String url,
	                          String user,
	                          String password) throws SQLException, ClassNotFoundException {
	    fieldMap.put(DatabaseProperty.DRIVER_PROPERTY, driver);
	    fieldMap.put(DatabaseProperty.URL_PROPERTY, url);
	    fieldMap.put(DatabaseProperty.USERNAME_PROPERTY, user);
	    fieldMap.put(DatabaseProperty.PASSWORD_PROPERTY, password);
	    Class.forName(getDriver());
	    connect();
	    try {
	        findAllTables();
	    }
	    finally {
	        disconnect();
	    }
	}
	
	public CPDatabaseRepository(String repositoryDescriptor) throws ClassNotFoundException, SQLException {
		List<String> fields = parse(repositoryDescriptor);
		for (DatabaseProperty field : DATABASE_FIELDS) {
			fieldMap.put(field, fields.get(getDBPropertyIndex(field)));
		}
		Class.forName(getDriver());
		connect();
		try {
		    for (int index = DATABASE_FIELDS.length; index < fields.size(); index++) {
		        String table = fields.get(index);
		        addTable(table);
		        allTables.add(table);
		    }
		} finally {
		    disconnect();
		}
	}


	
	private void findAllTables() throws SQLException {
	    DatabaseMetaData metaData = connection.getMetaData();
	    ResultSet tableTypesSet = metaData.getTableTypes();
	    List<String> tableTypes = new ArrayList<String>();
	    while (tableTypesSet.next()) {
	        String tableType = tableTypesSet.getString(SQL_GET_TABLE_TYPES_TABLE_TYPE_COL);
	        if (tableType.equals(SQL_TABLE_TYPE) || tableType.equals(SQL_VIEW_TYPE)) {
	            tableTypes.add(tableType);
	        }
	    }
	    ResultSet tableSet = metaData.getTables(null, null, null, tableTypes.toArray(new String[1]));
	    String aSuffix = "_FRAME";
	    while (tableSet.next()) {
	        String table = tableSet.getString(SQL_GET_TABLES_TABLENAME_COL);

	        // Use case insensitive string comparison here because depending on the operating
	        // system and database configuration table names may have been converted to lower
	        // case so the table name might look like XXX_frame. With case sensitive comparison
	        // we might miss existing tables.
	        if (table.length() > aSuffix.length() && 
	        		table.substring(table.length() - aSuffix.length()).equalsIgnoreCase(aSuffix) &&
	                addTable(table = table.substring(0, table.length() - aSuffix.length()))) {
	            allTables.add(table);
	        }
	    }
	    if (allTables.isEmpty()) {
	        throw new SQLException("No tables containing ontologies found");
	    }
	}
	
	public void connect() throws SQLException {
		connection = DriverManager.getConnection(getUrl(), getUser(), getPassword());
	}
	
	public void disconnect() throws SQLException {
		connection.close();
		connection = null;
	}
	
	public boolean addTable(String table) {
        String ontology = null;
	    try {
	        ontology = DatabaseFactoryUtils.getOntologyFromTable(
	                CPDatabaseFrameDb.class,
					getDriver(), getUrl(), getUser(), getPassword(), table );
	        if (ontology != null) {
	        	URI ontologyURI = new URI(ontology);
	            ontologyToTable.put(ontologyURI, table);
	            tableToOntology.put(table, ontologyURI);
	            return true;
	        }
	    }
	    catch (SQLException e) {
	        if (log.isLoggable(Level.FINE)) {
	            log.log(Level.FINE, "Exception caught looking for ontology in db table " + table, e);
	        }
	    }
	    catch (URISyntaxException e) {
	        if (log.isLoggable(Level.FINE)) {
	            log.log(Level.FINE, "Ontology " + ontology + " found in " + table + " not in uri format.", e);
	        } 
	    }
        return false;
	}

	@SuppressWarnings("unchecked")
    public TripleStore loadImportedAssertions(OWLModel owlModel, URI ontologyName)
			throws OntologyLoadException {
	    String table = ontologyToTable.get(ontologyName);
	    DatabaseFrameDb dbFrameStore = DatabaseFrameDbFactory.createDatabaseFrameDb(CPDatabaseFrameDb.class);
	    dbFrameStore.initialize(owlModel.getOWLJavaFactory(), getDriver(), getUrl(), getUser(), getPassword(), table, true);
	    IdleConnectionNarrowFrameStore nfs  = new IdleConnectionNarrowFrameStore(new ValueCachingNarrowFrameStore(dbFrameStore));
	    nfs.setName(ontologyName.toString());
	    TripleStoreModel tripleStoreModel = owlModel.getTripleStoreModel();
	    TripleStore importedTripleStore = null;
	    TripleStore importingTripleStore = tripleStoreModel.getActiveTripleStore();
	    try {
	        importedTripleStore = tripleStoreModel.createActiveImportedTripleStore(nfs);
	        Collection errors = new ArrayList();
	        DatabaseFactoryUtils.readOWLOntologyFromDatabase(owlModel, importedTripleStore);
	        FactoryUtils.loadEncodedNamespaceFromModel(owlModel, importedTripleStore, errors);
	        FactoryUtils.addPrefixesToModelListener(owlModel, importedTripleStore);
	        DatabaseFactoryUtils.loadImports(owlModel, errors);
	        if (!errors.isEmpty()) {
	            throw new AmalgamatedLoadException(errors);
	        }
	    }
	    finally {
	        tripleStoreModel.setActiveTripleStore(importingTripleStore);
	    }
	    return importedTripleStore;
	}

	public boolean contains(URI ontologyName) {
	    return ontologyToTable.keySet().contains(ontologyName);
	}

	public Collection<URI> getOntologies() {
	    return Collections.unmodifiableCollection(ontologyToTable.keySet());
	}

	public String getOntologyLocationDescription(URI ontologyName) {
		return "Tables " + ontologyToTable.get(ontologyName) + "_* of the database " + getUrl();
	}

	public OutputStream getOutputStream(URI ontologyName) throws IOException {
		return null;
	}

	public String getRepositoryDescription() {
		return "Repository for the database " + getUrl();
	}

	public String getRepositoryDescriptor() {
	    StringBuffer sb = new StringBuffer();
	    sb.append(REPOSITORY_DESCRIPTOR_PREFIX);
	    for (DatabaseProperty field : DATABASE_FIELDS) {
	        sb.append(fieldMap.get(field));
	        sb.append(SEPARATOR_CHAR);
	    }
	    for (String table : allTables) {
	        sb.append(table);
	        sb.append(SEPARATOR_CHAR);
	    }
	    
	    // Strip the trailing comma at the end
		return sb.substring(0, sb.length() - 1);
	}

	public boolean isSystem() {
		return false;
	}

	public boolean isWritable(URI ontologyName) {
		return true;
	}
	
	public boolean hasOutputStream(URI ontologyName) {
	    return false;
	}

	public void refresh() {
	    // not sure if this should look at all the tables in the database or just 
	    // request the ones selected...  When am i called?
	}

	public String getDriver() {
		return fieldMap.get(DatabaseProperty.DRIVER_PROPERTY);
	}
	
	public String getUrl() {
		return fieldMap.get(DatabaseProperty.URL_PROPERTY);
	}
	
	public String getUser() {
		return fieldMap.get(DatabaseProperty.USERNAME_PROPERTY);
	}

	public String getPassword() {
		return fieldMap.get(DatabaseProperty.PASSWORD_PROPERTY);
	}
	
	public Map<String, URI> getTableToOntologyMap() { 
		return new HashMap<String, URI>(tableToOntology);
	}
}
